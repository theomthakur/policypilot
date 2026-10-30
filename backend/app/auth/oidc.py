"""OpenID Connect sign-in: Authorization Code flow with PKCE, state and nonce (RFC 9700 guidance).

Authlib performs the protocol steps. Provider tokens never reach the browser: the callback exchanges the
code on the server, validates the ID token (signature, issuer, audience, expiry, nonce) and then issues
PolicyPilot's own opaque session cookie.
"""

import secrets
import time
from dataclasses import dataclass
from typing import Any

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from joserfc import jwt
from joserfc.jwk import KeySet, OctKey

from app.config import Settings

FLOW_TTL_SECONDS = 600


class OidcError(Exception):
    """Sign-in could not be completed. The message is safe to show; details stay in the logs."""


@dataclass(frozen=True)
class Identity:
    issuer: str
    subject: str
    email: str | None
    name: str | None


def redirect_uri(settings: Settings) -> str:
    return settings.oidc_redirect_uri or f"{settings.public_origin.rstrip('/')}/api/v1/auth/callback"


def _internal(settings: Settings, url: str) -> str:
    """Reach the provider by its in-cluster/in-container address when one is configured."""
    if settings.oidc_internal_issuer and url.startswith(settings.oidc_issuer):
        return settings.oidc_internal_issuer + url.removeprefix(settings.oidc_issuer)
    return url


async def discovery(settings: Settings) -> dict[str, Any]:
    base = settings.oidc_internal_issuer or settings.oidc_issuer
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base.rstrip('/')}/.well-known/openid-configuration")
            response.raise_for_status()
            doc = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise OidcError("The sign-in provider is unavailable.") from exc
    if doc.get("issuer", "").rstrip("/") != settings.oidc_issuer.rstrip("/"):
        raise OidcError("The sign-in provider reported an unexpected issuer.")
    return dict(doc)


def _flow_key(settings: Settings) -> OctKey:
    return OctKey.import_key(settings.auth_secret_key)


# Asymmetric algorithms an ID token may use. "none" and shared-secret algorithms are never accepted.
ID_TOKEN_ALGORITHMS = ["RS256", "RS384", "RS512", "PS256", "ES256", "ES384", "EdDSA"]


def _client(settings: Settings, **kwargs: Any) -> AsyncOAuth2Client:
    return AsyncOAuth2Client(
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret or None,
        scope="openid email profile",
        # A public client (no secret) authenticates the code exchange with PKCE alone.
        token_endpoint_auth_method="client_secret_basic" if settings.oidc_client_secret else "none",
        redirect_uri=redirect_uri(settings),
        code_challenge_method="S256",
        timeout=10.0,
        **kwargs,
    )


async def begin_login(settings: Settings, force_prompt: bool = False) -> tuple[str, str]:
    """Returns (authorization URL, signed flow cookie value)."""
    doc = await discovery(settings)
    state, nonce, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(24), secrets.token_urlsafe(48)
    async with _client(settings) as client:
        extra = {"prompt": "login"} if force_prompt else {}  # after a logout: ask for credentials again
        url, _ = client.create_authorization_url(
            doc["authorization_endpoint"], state=state, nonce=nonce, code_verifier=verifier, **extra
        )
    flow = jwt.encode(
        {"alg": "HS256"},
        {"state": state, "nonce": nonce, "verifier": verifier, "exp": int(time.time()) + FLOW_TTL_SECONDS},
        _flow_key(settings),
    )
    return str(url), flow


def _read_flow(settings: Settings, cookie: str | None) -> dict[str, Any]:
    if not cookie:
        raise OidcError("The sign-in attempt expired. Please try again.")
    try:
        token = jwt.decode(cookie, _flow_key(settings), algorithms=["HS256"])
        jwt.JWTClaimsRegistry(exp={"essential": True}).validate(token.claims)
    except Exception as exc:
        raise OidcError("The sign-in attempt expired. Please try again.") from exc
    return dict(token.claims)


async def finish_login(settings: Settings, flow_cookie: str | None, state: str, code: str) -> Identity:
    flow = _read_flow(settings, flow_cookie)
    if not secrets.compare_digest(str(flow.get("state", "")).encode(), state.encode()):
        raise OidcError("The sign-in response did not match this browser. Please try again.")
    doc = await discovery(settings)
    try:
        async with _client(settings) as client:
            token = await client.fetch_token(
                _internal(settings, doc["token_endpoint"]),
                grant_type="authorization_code",
                code=code,
                code_verifier=flow["verifier"],
            )
        async with httpx.AsyncClient(timeout=5.0) as http:
            jwks = (await http.get(_internal(settings, doc["jwks_uri"]))).json()
        id_token = token.get("id_token")
        if not id_token:
            raise OidcError("The provider did not return an identity.")
        decoded = jwt.decode(id_token, KeySet.import_key_set(jwks), algorithms=ID_TOKEN_ALGORITHMS)
        jwt.JWTClaimsRegistry(
            iss={"essential": True, "value": settings.oidc_issuer},
            aud={"essential": True, "value": settings.oidc_client_id},
            exp={"essential": True},
            sub={"essential": True},
        ).validate(decoded.claims)
        claims = decoded.claims
    except OidcError:
        raise
    except Exception as exc:
        raise OidcError("Sign-in could not be verified.") from exc
    if not secrets.compare_digest(str(claims.get("nonce", "")).encode(), str(flow["nonce"]).encode()):
        raise OidcError("Sign-in could not be verified.")
    audience = claims.get("aud")
    if isinstance(audience, list) and len(audience) > 1 and claims.get("azp") != settings.oidc_client_id:
        raise OidcError("Sign-in could not be verified.")  # OIDC Core: several audiences need a matching azp
    return Identity(
        issuer=settings.oidc_issuer,
        subject=str(claims["sub"]),
        email=claims.get("email"),
        name=claims.get("name") or claims.get("preferred_username"),
    )
