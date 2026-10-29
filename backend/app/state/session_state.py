"""Conversation state for a session: recent turns and any pending clarification.

Redis holds the hot copy (expiring with the session TTL); Postgres sessions.state is the durable copy,
so a Redis outage only costs a database read.
"""

import contextlib
import json
import uuid
from typing import Any

from redis.exceptions import RedisError
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Session, utcnow
from app.state.redis import get_redis

MAX_HISTORY = 6


def _key(session_id: uuid.UUID) -> str:
    return f"session:{session_id}"


def empty() -> dict[str, Any]:
    return {"history": [], "pending_clarification": None}


async def load(db: AsyncSession, session_id: uuid.UUID) -> dict[str, Any] | None:
    """Return the session state, or None when the session does not exist."""
    try:
        raw = await get_redis().get(_key(session_id))
        if raw:
            return json.loads(raw)  # type: ignore[no-any-return]
    except (RedisError, OSError, ValueError):
        pass
    row = await db.get(Session, session_id)
    if row is None:
        return None
    state = {**empty(), **(row.state or {})}
    await _mirror(session_id, state)
    return state


async def _mirror(session_id: uuid.UUID, state: dict[str, Any]) -> None:
    with contextlib.suppress(RedisError, OSError):
        await get_redis().set(_key(session_id), json.dumps(state), ex=get_settings().session_ttl_seconds)


async def save(db: AsyncSession, session_id: uuid.UUID, state: dict[str, Any]) -> None:
    state["history"] = state["history"][-MAX_HISTORY:]
    await db.execute(
        update(Session).where(Session.id == session_id).values(state=state, last_active_at=utcnow())
    )
    await db.commit()
    await _mirror(session_id, state)
