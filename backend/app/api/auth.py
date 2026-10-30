"""Sign-in routes: OIDC login and callback, the current user, logout, and a test-only provider."""

from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.api.deps import AUTH_COOKIE, SESSION_COOKIE, CurrentUser, DbSession
from app.api.errors import ApiError
from app.auth import oidc, service
from app.auth.oidc import Identity, OidcError
from app.config import Settings, get_settings
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
FLOW_COOKIE = "pp_flow"
logger = __import__("logging").getLogger("policypilot.auth")


def _user_json(user: User) -> dict[str, Any]:
    return {"id": str(user.id), "email": user.email, "name": user.name}


def _set_login_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        AUTH_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
        max_age=settings.auth_session_ttl_seconds,
        path="/",
    )


@router.get("/me")
async def me(db: DbSession, user: CurrentUser) -> dict[str, Any]:
    settings = get_settings()
    latest = await service.latest_session_id(db, user) if user else None
    return {
        "mode": settings.auth_mode,
        "authenticated": user is not None or settings.auth_mode == "off",
        "user": _user_json(user) if user else None,
        "latest_session_id": str(latest) if latest else None,
    }


RELOGIN_COOKIE = "pp_relogin"


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    settings = get_settings()
    if settings.auth_mode != "oidc":
        raise ApiError(404, "NOT_FOUND", "Sign-in with a provider is not enabled.")
    try:
        url, flow = await oidc.begin_login(settings, force_prompt=RELOGIN_COOKIE in request.cookies)
    except OidcError as exc:
        raise ApiError(503, "AUTH_UNAVAILABLE", str(exc)) from exc
    response = RedirectResponse(url, status_code=302)
    response.delete_cookie(RELOGIN_COOKIE, path="/api/v1/auth")
    response.set_cookie(
        FLOW_COOKIE,
        flow,
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
        max_age=oidc.FLOW_TTL_SECONDS,
        path="/api/v1/auth",
    )
    return response


@router.get("/callback")
async def callback(
    request: Request,
    db: DbSession,
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
    pp_flow: Annotated[str | None, Cookie()] = None,
) -> RedirectResponse:
    settings = get_settings()
    if settings.auth_mode != "oidc":
        raise ApiError(404, "NOT_FOUND", "Sign-in with a provider is not enabled.")
    failure = RedirectResponse("/?auth_error=1", status_code=303)
    failure.delete_cookie(FLOW_COOKIE, path="/api/v1/auth")
    if error or not code or not state:
        return failure
    try:
        identity = await oidc.finish_login(settings, pp_flow, state, code)
    except OidcError as exc:
        logger.warning("sign-in rejected: %s", exc)
        return failure
    user = await service.upsert_user(db, identity)
    await service.revoke(
        db, request.cookies.get(AUTH_COOKIE)
    )  # a signed-in browser signing in again drops its old login
    token = await service.start_session(db, user, settings)
    response = RedirectResponse("/", status_code=303)
    _set_login_cookie(response, token, settings)
    response.delete_cookie(FLOW_COOKIE, path="/api/v1/auth")
    return response


class TestLogin(BaseModel):
    subject: str = Field(min_length=1, max_length=100)
    email: str | None = None
    name: str | None = None


@router.post("/test-login")
async def test_login(body: TestLogin, response: Response, db: DbSession) -> dict[str, Any]:
    """A fake provider for automated tests. Only exists when AUTH_MODE=test, which production refuses."""
    settings = get_settings()
    if settings.auth_mode != "test" or settings.app_env == "production":
        raise ApiError(404, "NOT_FOUND", "Not found.")
    user = await service.upsert_user(db, Identity("test-provider", body.subject, body.email, body.name))
    token = await service.start_session(db, user, settings)
    _set_login_cookie(response, token, settings)
    return _user_json(user)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, db: DbSession) -> None:
    await service.revoke(db, request.cookies.get(AUTH_COOKIE))
    response.delete_cookie(AUTH_COOKIE, path="/")
    response.delete_cookie(SESSION_COOKIE, path="/")
    # The provider's own session may still be open; make the next sign-in ask for credentials again.
    response.set_cookie(RELOGIN_COOKIE, "1", httponly=True, samesite="lax", max_age=3600, path="/api/v1/auth")
