"""Shared request dependencies."""

import uuid
from typing import Annotated

from fastapi import Cookie, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError
from app.config import get_settings
from app.db.session import get_db

SESSION_COOKIE = "pp_session"

DbSession = Annotated[AsyncSession, Depends(get_db)]


def current_session_id(pp_session: Annotated[str | None, Cookie()] = None) -> uuid.UUID | None:
    if not pp_session:
        return None
    try:
        return uuid.UUID(pp_session)
    except ValueError:
        return None


CurrentSession = Annotated[uuid.UUID | None, Depends(current_session_id)]


def require_passcode(x_demo_passcode: Annotated[str | None, Header()] = None) -> None:
    """Gate for the actions that create state or spend money (session, upload, message).

    Everything else is gated by owning the session cookie that the passcode-protected call returns; the
    browser's event stream cannot send custom headers, so the cookie is the only gate it can carry.
    """
    expected = get_settings().demo_passcode
    if expected and x_demo_passcode != expected:
        raise ApiError(401, "PASSCODE_REQUIRED", "A valid demo passcode is required.")


Passcode = Depends(require_passcode)


def require_owner(session_id: uuid.UUID, current: uuid.UUID | None) -> None:
    """404 (not 403) unless the cookie owns `session_id`, so resource existence is not revealed."""
    if current is None or current != session_id:
        raise ApiError(404, "NOT_FOUND", "Session not found.")
