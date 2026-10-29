"""Turns: start one, read it, stream its trace (contracts/openapi.yaml)."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentSession, DbSession, require_owner, require_passcode
from app.api.errors import ApiError
from app.db.models import Session, TraceEvent, Turn
from app.state import limits, session_state
from app.turns import service

router = APIRouter(tags=["turns"])
STREAM_MAX_SECONDS = 150


class MessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    mode: Literal["agent", "baseline"] = "agent"
    reply_to_clarification: uuid.UUID | None = None
    fault_inject: str | None = None


def event_json(event: TraceEvent) -> dict[str, Any]:
    return {
        "turn_id": str(event.turn_id),
        "seq": event.seq,
        "ts": event.created_at.isoformat(),
        "type": event.type,
        **event.payload,
    }


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


@router.post("/sessions/{session_id}/messages", status_code=202)
async def post_message(
    session_id: uuid.UUID,
    body: MessageRequest,
    request: Request,
    db: DbSession,
    current: CurrentSession,
    x_demo_passcode: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    require_passcode(x_demo_passcode)
    require_owner(session_id, current)
    if await db.get(Session, session_id) is None:
        raise ApiError(404, "NOT_FOUND", "Session not found.")
    await limits.check_rate_limit(_client_key(request))
    content = body.content.strip()
    if not content:
        raise ApiError(400, "INVALID_ARGUMENT", "Message must not be empty.")
    if body.reply_to_clarification is not None:
        state = await session_state.load(db, session_id) or session_state.empty()
        pending = state.get("pending_clarification")
        if not pending or pending.get("turn_id") != str(body.reply_to_clarification):
            raise ApiError(400, "INVALID_ARGUMENT", "No pending clarification with that id.")
    turn = Turn(
        session_id=session_id, question=content, mode=body.mode, reply_to_turn_id=body.reply_to_clarification
    )
    db.add(turn)
    await db.commit()
    service.spawn(turn.id, session_id, body.fault_inject, body.reply_to_clarification)
    return {"turn_id": str(turn.id), "session_id": str(session_id)}


async def _turn_or_404(db: DbSession, turn_id: uuid.UUID, current: uuid.UUID | None) -> Turn:
    turn = await db.get(Turn, turn_id)
    if turn is None or current is None or turn.session_id != current:
        raise ApiError(404, "NOT_FOUND", "Turn not found.")
    return turn


@router.get("/turns/{turn_id}")
async def get_turn(turn_id: uuid.UUID, db: DbSession, current: CurrentSession) -> dict[str, Any]:
    turn = await _turn_or_404(db, turn_id, current)
    events = (
        await db.execute(select(TraceEvent).where(TraceEvent.turn_id == turn_id).order_by(TraceEvent.seq))
    ).scalars()
    return {
        "id": str(turn.id),
        "session_id": str(turn.session_id),
        "question": turn.question,
        "mode": turn.mode,
        "status": turn.status,
        "stop_reason": turn.stop_reason,
        "answer": turn.answer,
        "clarification": turn.clarification,
        "events": [event_json(e) for e in events],
        "totals": turn.totals
        or {
            "steps": 0,
            "tool_calls": 0,
            "query_revisions": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": 0,
        },
        "created_at": turn.created_at.isoformat(),
    }


@router.get("/turns/{turn_id}/events")
async def stream_events(
    turn_id: uuid.UUID, request: Request, db: DbSession, current: CurrentSession
) -> StreamingResponse:
    await _turn_or_404(db, turn_id, current)

    async def frames() -> AsyncIterator[str]:
        last, waited, idle = -1, 0.0, 0.0
        while waited < STREAM_MAX_SECONDS:
            if await request.is_disconnected():
                return
            events = await service.load_events(turn_id, last)
            for event in events:
                last = event.seq
                yield f"event: {event.type}\ndata: {json.dumps(event_json(event))}\n\n"
                if event.type == "turn_completed":
                    return
            if events:
                idle = 0.0
            else:
                idle += 0.25
                if idle >= 10:  # keep proxies from closing a quiet stream
                    yield ": keep-alive\n\n"
                    idle = 0.0
            await asyncio.sleep(0.25)
            waited += 0.25

    return StreamingResponse(
        frames(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
