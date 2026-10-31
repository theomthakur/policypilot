"""Authentication and ownership against a real local OpenID Connect provider (RSA-signed tokens, PKCE).

The provider is a small ASGI app on a loopback port, so the backend's discovery, token exchange and ID-token
validation run exactly as they would against Keycloak. Each rejection path (state, nonce, issuer, audience,
expiry, signature, provider outage) is exercised, then two users are checked for isolation.
"""

import asyncio
import base64
import hashlib
import secrets
import socket
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from joserfc import jwt
from joserfc.jwk import RSAKey
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route

from tests.integration.conftest import clear_caches

CLIENT_ID = "policypilot"
ORIGIN = "http://testserver"


class Provider:
    """A minimal OIDC provider. `behaviour` bends one aspect of the next token to test a rejection."""

    def __init__(self) -> None:
        self.key = RSAKey.generate_key(2048, {"kid": "k1", "use": "sig"})
        self.other_key = RSAKey.generate_key(2048, {"kid": "k1", "use": "sig"})  # same kid, different key
        self.codes: dict[str, dict[str, Any]] = {}
        self.behaviour = "ok"
        self.subject = "user-a"
        self.port = _free_port()
        self.issuer = f"http://127.0.0.1:{self.port}"

    def app(self) -> Starlette:
        async def discovery(_: Request) -> JSONResponse:
            return JSONResponse(
                {
                    "issuer": self.issuer,
                    "authorization_endpoint": f"{self.issuer}/authorize",
                    "token_endpoint": f"{self.issuer}/token",
                    "jwks_uri": f"{self.issuer}/jwks",
                }
            )

        async def jwks(_: Request) -> JSONResponse:
            return JSONResponse({"keys": [self.key.as_dict(private=False)]})

        async def authorize(request: Request) -> RedirectResponse:
            q = request.query_params
            code = secrets.token_urlsafe(16)
            self.codes[code] = {
                "nonce": q["nonce"],
                "challenge": q["code_challenge"],
                "client": q["client_id"],
                "sub": self.subject,
            }
            return RedirectResponse(f"{q['redirect_uri']}?code={code}&state={q['state']}")

        async def token(request: Request) -> JSONResponse:
            form = await request.form()
            entry = self.codes.pop(str(form["code"]), None)
            if entry is None:
                return JSONResponse({"error": "invalid_grant"}, status_code=400)
            digest = hashlib.sha256(str(form["code_verifier"]).encode()).digest()
            if base64.urlsafe_b64encode(digest).rstrip(b"=").decode() != entry["challenge"]:
                return JSONResponse({"error": "invalid_grant"}, status_code=400)
            now = int(time.time())
            claims: dict[str, Any] = {
                "iss": self.issuer,
                "aud": CLIENT_ID,
                "sub": entry["sub"],
                "email": f"{entry['sub']}@example.test",
                "name": entry["sub"].title(),
                "nonce": entry["nonce"],
                "iat": now,
                "exp": now + 300,
            }
            key = self.key
            if self.behaviour == "wrong_nonce":
                claims["nonce"] = "someone-elses-nonce"
            elif self.behaviour == "wrong_issuer":
                claims["iss"] = "http://evil.example"
            elif self.behaviour == "wrong_audience":
                claims["aud"] = "another-client"
            elif self.behaviour == "multi_audience":
                claims["aud"] = [CLIENT_ID, "another-client"]  # no azp
            elif self.behaviour == "expired":
                claims["exp"] = now - 60
            elif self.behaviour == "bad_signature":
                key = self.other_key
            id_token = jwt.encode({"alg": "RS256", "kid": "k1"}, claims, key)
            return JSONResponse({"access_token": "opaque", "token_type": "Bearer", "id_token": id_token})

        return Starlette(
            routes=[
                Route("/.well-known/openid-configuration", discovery),
                Route("/jwks", jwks),
                Route("/authorize", authorize),
                Route("/token", token, methods=["POST"]),
            ]
        )


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def provider() -> Iterator[Provider]:
    p = Provider()
    server = uvicorn.Server(uvicorn.Config(p.app(), host="127.0.0.1", port=p.port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield p
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def oidc_env(monkeypatch: pytest.MonkeyPatch, provider: Provider) -> Provider:
    for key, value in {
        "AUTH_MODE": "oidc",
        "OIDC_ISSUER": provider.issuer,
        "OIDC_CLIENT_ID": CLIENT_ID,
        "OIDC_CLIENT_SECRET": "not-a-real-secret",
        "AUTH_SECRET_KEY": "x" * 40,
        "PUBLIC_ORIGIN": ORIGIN,
    }.items():
        monkeypatch.setenv(key, value)
    clear_caches()
    return provider


def _app_client() -> TestClient:
    from app.main import create_app

    clear_caches()
    client = TestClient(create_app(), base_url=ORIGIN)
    client.__enter__()
    return client


def _sign_in(client: TestClient, tamper_state: bool = False) -> httpx.Response:
    """Walk the real redirect chain: app -> provider -> app callback."""
    login = client.get("/api/v1/auth/login", follow_redirects=False)
    assert login.status_code == 302
    with httpx.Client(follow_redirects=False) as browser:
        back = browser.get(login.headers["location"])
    callback = urlparse(back.headers["location"])
    query = parse_qs(callback.query)
    state = "forged" if tamper_state else query["state"][0]
    return client.get(f"{callback.path}?code={query['code'][0]}&state={state}", follow_redirects=False)


def _signed_in_client(subject: str, provider: Provider) -> TestClient:
    provider.subject = subject
    client = _app_client()
    result = _sign_in(client)
    assert result.status_code == 303 and result.headers["location"] == "/", result.headers
    assert "pp_auth" in client.cookies
    return client


def test_successful_sign_in_creates_a_user_and_a_cookie_session(oidc_env: Provider) -> None:
    client = _signed_in_client("user-a", oidc_env)
    me = client.get("/api/v1/auth/me").json()
    assert me["mode"] == "oidc" and me["authenticated"] is True
    assert me["user"]["email"] == "user-a@example.test"
    assert client.get("/api/v1/documents").status_code == 200


def test_protected_routes_need_a_signed_in_user(oidc_env: Provider) -> None:
    client = _app_client()
    for method, path in (("get", "/api/v1/documents"), ("post", "/api/v1/sessions")):
        response = getattr(client, method)(path)
        assert response.status_code == 401 and response.json()["error"]["code"] == "AUTH_REQUIRED"
    assert client.get("/api/v1/auth/me").json()["authenticated"] is False
    assert client.get("/api/v1/health/live").status_code == 200  # health stays open


def test_a_forged_state_is_rejected(oidc_env: Provider) -> None:
    client = _app_client()
    result = _sign_in(client, tamper_state=True)
    assert result.status_code == 303 and "auth_error" in result.headers["location"]
    assert "pp_auth" not in client.cookies


@pytest.mark.parametrize(
    "behaviour", ["wrong_nonce", "wrong_issuer", "wrong_audience", "expired", "bad_signature"]
)
def test_an_invalid_id_token_is_rejected(oidc_env: Provider, behaviour: str) -> None:
    oidc_env.behaviour = behaviour
    client = _app_client()
    result = _sign_in(client)
    assert "auth_error" in result.headers["location"], behaviour
    assert "pp_auth" not in client.cookies
    assert client.get("/api/v1/documents").status_code == 401


def test_a_replayed_authorization_code_is_rejected(oidc_env: Provider) -> None:
    client = _app_client()
    login = client.get("/api/v1/auth/login", follow_redirects=False)
    with httpx.Client(follow_redirects=False) as browser:
        back = browser.get(login.headers["location"])
    callback = urlparse(back.headers["location"])
    first = client.get(f"{callback.path}?{callback.query}", follow_redirects=False)
    assert first.headers["location"] == "/"
    client.cookies.clear()  # a different browser replaying the captured URL has no flow cookie
    replay = client.get(f"{callback.path}?{callback.query}", follow_redirects=False)
    assert "auth_error" in replay.headers["location"] and "pp_auth" not in client.cookies


def test_provider_outage_is_reported_not_hung(oidc_env: Provider, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OIDC_ISSUER", f"http://127.0.0.1:{_free_port()}")
    clear_caches()
    client = _app_client()
    response = client.get("/api/v1/auth/login", follow_redirects=False)
    assert response.status_code == 503 and response.json()["error"]["code"] == "AUTH_UNAVAILABLE"


def test_logout_revokes_the_login_everywhere(oidc_env: Provider) -> None:
    client = _signed_in_client("user-a", oidc_env)
    token = client.cookies["pp_auth"]
    assert client.post("/api/v1/auth/logout", headers={"Origin": ORIGIN}).status_code == 204
    stolen = _app_client()
    stolen.cookies.set("pp_auth", token)
    assert stolen.get("/api/v1/documents").status_code == 401  # the old cookie is dead server-side


def test_an_expired_login_session_stops_working(oidc_env: Provider) -> None:
    from sqlalchemy import update

    from app.db.models import AuthSession
    from app.db.session import get_sessionmaker

    client = _signed_in_client("user-a", oidc_env)

    async def expire() -> None:
        async with get_sessionmaker()() as db:
            await db.execute(update(AuthSession).values(expires_at="2000-01-01T00:00:00Z"))
            await db.commit()

    asyncio.run(expire())
    clear_caches()
    assert client.get("/api/v1/documents").status_code == 401


def test_cross_site_requests_with_the_login_cookie_are_refused(oidc_env: Provider) -> None:
    client = _signed_in_client("user-a", oidc_env)
    evil = client.post("/api/v1/sessions", headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403 and evil.json()["error"]["code"] == "FORBIDDEN"
    fetch_site = client.post("/api/v1/sessions", headers={"Sec-Fetch-Site": "cross-site"})
    assert fetch_site.status_code == 403
    assert client.post("/api/v1/sessions", headers={"Origin": ORIGIN}).status_code == 201


def _become(client: TestClient, cookies: dict[str, str]) -> None:
    """Act as another browser on the same app: swap the cookie jar."""
    client.cookies.clear()
    for name, value in cookies.items():
        client.cookies.set(name, value)


def _jar(client: TestClient) -> dict[str, str]:
    return {cookie.name: str(cookie.value) for cookie in client.cookies.jar}


def test_two_users_cannot_see_each_others_conversations_or_uploads(
    oidc_env: Provider, make_pdf: Callable[..., Path]
) -> None:
    pdf = make_pdf(
        ["1. Private\n\nThe cafeteria vault code word is pelican-7731 and it opens at nine every morning."],
        name="secret.pdf",
    )
    client = _app_client()
    oidc_env.subject = "alice"
    assert _sign_in(client).headers["location"] == "/"
    assert client.post("/api/v1/sessions", headers={"Origin": ORIGIN}).status_code == 201
    alice_session = client.cookies["pp_session"]
    uploaded = client.post(
        "/api/v1/documents", files={"file": ("secret.pdf", pdf.read_bytes(), "application/pdf")}
    )
    assert uploaded.status_code == 201
    doc_id, run_id = uploaded.json()["document"]["id"], uploaded.json()["ingestion_run"]["id"]
    assert client.get(f"/api/v1/sessions/{alice_session}").status_code == 200
    assert doc_id in {d["id"] for d in client.get("/api/v1/documents").json()["items"]}

    # Uploads belong to Alice's personal library, not only to the conversation that added them.
    assert client.post("/api/v1/sessions", headers={"Origin": ORIGIN}).status_code == 201
    assert doc_id in {d["id"] for d in client.get("/api/v1/documents").json()["items"]}
    assert client.get(f"/api/v1/documents/{doc_id}").status_code == 200
    client.cookies.set("pp_session", alice_session)
    alice = _jar(client)

    client.cookies.clear()
    oidc_env.subject = "bob"
    assert _sign_in(client).headers["location"] == "/"
    assert client.post("/api/v1/sessions", headers={"Origin": ORIGIN}).status_code == 201
    bob = _jar(client)
    assert alice["pp_auth"] != bob["pp_auth"] and alice_session != bob["pp_session"]

    # Bob presents Alice's conversation id as his own cookie: an id is a name, not proof of ownership.
    _become(client, {**bob, "pp_session": alice_session})
    assert client.get(f"/api/v1/sessions/{alice_session}").status_code == 404
    assert (
        client.post(f"/api/v1/sessions/{alice_session}/messages", json={"content": "hi"}).status_code == 404
    )
    assert (
        client.post(f"/api/v1/sessions/{alice_session}/resume", headers={"Origin": ORIGIN}).status_code == 404
    )
    _become(client, bob)
    for path in (
        f"/api/v1/documents/{doc_id}",
        f"/api/v1/documents/{doc_id}/pages/1",
        f"/api/v1/documents/{doc_id}/file",
        f"/api/v1/ingestion/{run_id}",
    ):
        assert client.get(path).status_code == 404, path
    assert doc_id not in {d["id"] for d in client.get("/api/v1/documents").json()["items"]}

    _become(client, alice)  # and Alice still has everything
    assert doc_id in {d["id"] for d in client.get("/api/v1/documents").json()["items"]}
    assert client.get(f"/api/v1/sessions/{alice_session}").status_code == 200


def test_a_user_can_pick_a_conversation_back_up_after_signing_in_again(oidc_env: Provider) -> None:
    client = _signed_in_client("alice", oidc_env)
    client.post("/api/v1/sessions", headers={"Origin": ORIGIN})
    session_id = client.cookies["pp_session"]
    client.post("/api/v1/auth/logout", headers={"Origin": ORIGIN})
    assert "pp_session" not in client.cookies

    oidc_env.subject = "alice"
    assert _sign_in(client).headers["location"] == "/"
    latest = client.get("/api/v1/auth/me").json()["latest_session_id"]
    assert latest == session_id
    resumed = client.post(f"/api/v1/sessions/{latest}/resume", headers={"Origin": ORIGIN})
    assert resumed.status_code == 200 and client.cookies["pp_session"] == session_id
    assert client.get(f"/api/v1/sessions/{session_id}").status_code == 200


def test_production_fails_closed_without_real_sign_in(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.auth.service import validate_settings
    from app.config import Settings

    base = {"app_env": "production", "public_origin": "https://example.org"}
    with pytest.raises(RuntimeError, match="AUTH_MODE"):
        validate_settings(Settings(**base, auth_mode="off"))  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="AUTH_MODE"):  # the opt-out also needs a passcode
        validate_settings(Settings(**base, auth_mode="off", allow_passcode_only_production=True))  # type: ignore[arg-type]
    validate_settings(  # a passcode-only demo, asked for by name
        Settings(  # type: ignore[arg-type]
            **base,
            auth_mode="off",
            allow_passcode_only_production=True,
            demo_passcode="x" * 12,
            auth_cookie_secure=True,
            session_cookie_secure=True,
        )
    )
    with pytest.raises(RuntimeError, match="COOKIE_SECURE"):  # production over HTTPS needs both Secure flags
        validate_settings(
            Settings(  # type: ignore[arg-type]
                **base,
                auth_mode="oidc",
                oidc_issuer="https://idp",
                oidc_client_id="c",
                auth_secret_key="x" * 40,
            )
        )
    with pytest.raises(RuntimeError, match="AUTH_MODE"):
        validate_settings(Settings(**base, auth_mode="test", auth_secret_key="x" * 40))  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="AUTH_SECRET_KEY"):
        validate_settings(
            Settings(**base, auth_mode="oidc", oidc_issuer="https://idp", oidc_client_id="c")  # type: ignore[arg-type]
        )
    validate_settings(
        Settings(  # type: ignore[arg-type]
            **base,
            auth_mode="oidc",
            oidc_issuer="https://idp",
            oidc_client_id="c",
            auth_secret_key="x" * 40,
            auth_cookie_secure=True,
            session_cookie_secure=True,
        )
    )


def test_the_test_provider_endpoint_is_absent_unless_test_mode(oidc_env: Provider) -> None:
    client = _app_client()
    assert client.post("/api/v1/auth/test-login", json={"subject": "x"}).status_code == 404


def test_a_non_ascii_state_is_a_normal_failure_not_a_server_error(oidc_env: Provider) -> None:
    client = _app_client()
    login = client.get("/api/v1/auth/login", follow_redirects=False)
    assert login.status_code == 302
    response = client.get("/api/v1/auth/callback?code=x&state=%C3%A9", follow_redirects=False)
    assert response.status_code == 303 and "auth_error" in response.headers["location"]


def test_signing_in_again_revokes_the_previous_login(oidc_env: Provider) -> None:
    client = _signed_in_client("user-a", oidc_env)
    first = client.cookies["pp_auth"]
    assert _sign_in(client).headers["location"] == "/"
    assert client.cookies["pp_auth"] != first
    stolen = _app_client()
    stolen.cookies.set("pp_auth", first)
    assert stolen.get("/api/v1/documents").status_code == 401  # the copied old token is dead


def test_the_next_sign_in_after_a_logout_asks_the_provider_for_credentials_again(oidc_env: Provider) -> None:
    client = _signed_in_client("user-a", oidc_env)
    client.post("/api/v1/auth/logout", headers={"Origin": ORIGIN})
    login = client.get("/api/v1/auth/login", follow_redirects=False)
    assert "prompt=login" in login.headers["location"]
    again = client.get("/api/v1/auth/login", follow_redirects=False)
    assert "prompt=login" not in again.headers["location"]  # only once


def test_two_first_sign_ins_for_one_person_make_one_user(oidc_env: Provider) -> None:
    import asyncio as aio

    from sqlalchemy import func, select

    from app.auth.oidc import Identity
    from app.auth.service import upsert_user
    from app.db.models import User
    from app.db.session import get_sessionmaker

    async def go() -> int:
        async def one() -> None:
            async with get_sessionmaker()() as db:
                await upsert_user(db, Identity("https://idp", "same-subject", "a@example.test", "A"))
                await db.commit()

        await aio.gather(one(), one(), one())
        async with get_sessionmaker()() as db:
            return int((await db.execute(select(func.count()).select_from(User))).scalar_one())

    clear_caches()
    try:
        assert aio.run(go()) == 1
    finally:
        clear_caches()


def test_a_token_for_several_audiences_needs_a_matching_azp(oidc_env: Provider) -> None:
    oidc_env.behaviour = "multi_audience"
    client = _app_client()
    result = _sign_in(client)
    assert "auth_error" in result.headers["location"] and "pp_auth" not in client.cookies
