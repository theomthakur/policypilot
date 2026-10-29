"""Shared request dependencies."""

import uuid
from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

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
