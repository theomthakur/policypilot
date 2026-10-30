"""What each kind of job does. Handlers are idempotent: running one twice yields one final result."""

import uuid
from pathlib import Path
from typing import Any

from app.jobs.queue import Claimed


async def handle(job: Claimed) -> None:
    if job.kind == "turn":
        from app.turns.service import run_turn

        p = job.payload
        reply = uuid.UUID(p["reply_to"]) if p.get("reply_to") else None
        await run_turn(uuid.UUID(p["turn_id"]), uuid.UUID(p["session_id"]), p.get("fault"), reply)
    elif job.kind == "ingest":
        from app.ingest.pipeline import ingest_document

        p = job.payload
        await ingest_document(uuid.UUID(p["document_id"]), uuid.UUID(p["run_id"]), Path(p["path"]))
    else:
        raise ValueError(f"unknown job kind {job.kind}")


async def on_interrupted(kind: str, payload: dict[str, Any], session_id: uuid.UUID | None) -> None:
    """A job used up its attempts after crashes: finish its records honestly, never leave them 'running'."""
    if kind == "turn":
        from app.turns.service import mark_interrupted

        await mark_interrupted(uuid.UUID(payload["turn_id"]))
    elif kind == "ingest":
        from app.ingest.pipeline import mark_ingest_interrupted

        await mark_ingest_interrupted(uuid.UUID(payload["document_id"]), uuid.UUID(payload["run_id"]))
