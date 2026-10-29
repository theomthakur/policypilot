"""Session creation. Full session state (Redis with Postgres fallback) arrives with WS1-22."""

import uuid
from typing import Any

from fastapi import APIRouter, Response
from sqlalchemy import select

from app.api.deps import SESSION_COOKIE, CurrentSession, DbSession, Passcode, require_owner
from app.api.errors import ApiError
from app.config import get_settings
from app.db.models import Session, Turn

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", status_code=201, dependencies=[Passcode])
async def create_session(response: Response, db: DbSession) -> dict[str, str]:
    session = Session()
    db.add(session)
    await db.commit()
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        str(session.id),
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        max_age=settings.session_ttl_seconds,
    )
    return {"session_id": str(session.id)}


@router.get("/{session_id}")
async def get_session(session_id: uuid.UUID, db: DbSession, current: CurrentSession) -> dict[str, Any]:
    require_owner(session_id, current)
    session = await db.get(Session, session_id)
    if session is None:
        raise ApiError(404, "NOT_FOUND", "Session not found.")
    turns = (
        await db.execute(select(Turn).where(Turn.session_id == session_id).order_by(Turn.created_at))
    ).scalars()
    return {
        "id": str(session.id),
        "created_at": session.created_at.isoformat(),
        "turns": [
            {
                "id": str(t.id),
                "question": t.question,
                "mode": t.mode,
                "status": t.status,
                "stop_reason": t.stop_reason,
                "created_at": t.created_at.isoformat(),
            }
            for t in turns
        ],
    }
