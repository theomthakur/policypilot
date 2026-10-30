"""Shared request dependencies."""

import secrets
import uuid
from typing import Annotated

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError
from app.auth.service import user_for_token
from app.config import get_settings
from app.db.models import Session, User
from app.db.session import get_db

SESSION_COOKIE = "pp_session"
AUTH_COOKIE = "pp_auth"

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def current_user(request: Request, db: DbSession) -> User | None:
    """The signed-in user, or None. Always None when authentication is off."""
    if get_settings().auth_mode == "off":
        return None
    return await user_for_token(db, request.cookies.get(AUTH_COOKIE))


CurrentUser = Annotated[User | None, Depends(current_user)]


def require_auth(user: CurrentUser) -> None:
    """401 on any protected route when authentication is on and nobody is signed in."""
    if get_settings().auth_mode != "off" and user is None:
        raise ApiError(401, "AUTH_REQUIRED", "Please sign in to continue.")


Authenticated = Depends(require_auth)


async def current_session_id(
    db: DbSession, user: CurrentUser, pp_session: Annotated[str | None, Cookie()] = None
) -> uuid.UUID | None:
    """The conversation this browser may use. A cookie only names a conversation: when authentication is on
    it counts only if the signed-in user owns it, so a copied or guessed id proves nothing."""
    if not pp_session:
        return None
    try:
        session_id = uuid.UUID(pp_session)
    except ValueError:
        return None
    if get_settings().auth_mode == "off":
        return session_id
    if user is None:
        return None
    owned = await db.get(Session, session_id)
    return session_id if owned is not None and owned.owner_user_id == user.id else None


CurrentSession = Annotated[uuid.UUID | None, Depends(current_session_id)]


def require_passcode(x_demo_passcode: Annotated[str | None, Header()] = None) -> None:
    """Gate for the actions that create state or spend money (session, upload, message).

    Everything else is gated by owning the session cookie that the passcode-protected call returns; the
    browser's event stream cannot send custom headers, so the cookie is the only gate it can carry.
    """
    expected = get_settings().demo_passcode
    if expected and not secrets.compare_digest((x_demo_passcode or "").encode(), expected.encode()):
        raise ApiError(401, "PASSCODE_REQUIRED", "A valid demo passcode is required.")


Passcode = Depends(require_passcode)


def require_owner(session_id: uuid.UUID, current: uuid.UUID | None) -> None:
    """404 (not 403) unless the cookie owns `session_id`, so resource existence is not revealed."""
    if current is None or current != session_id:
        raise ApiError(404, "NOT_FOUND", "Session not found.")


async def still_signed_in(request: Request) -> bool:
    """Used by long-lived streams: a logout, revocation or expiry ends the stream, not just new requests."""
    if get_settings().auth_mode == "off":
        return True
    from app.db.session import get_sessionmaker

    async with get_sessionmaker()() as db:
        return await user_for_token(db, request.cookies.get(AUTH_COOKIE)) is not None
