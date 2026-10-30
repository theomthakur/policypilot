"""The job table: enqueue, claim with a lease, heartbeat, and complete under a fencing check.

Delivery is at-least-once. A job can run again after a crash, so handlers are idempotent; a model call may be
repeated and billed twice. What is guaranteed is that only the worker holding the current fence can record
a result, and that one job never has two simultaneous owners.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job
from app.db.session import get_sessionmaker


@dataclass(frozen=True)
class Claimed:
    id: uuid.UUID
    kind: str
    payload: dict[str, Any]
    session_id: uuid.UUID | None
    fence: int
    attempts: int
    max_attempts: int


async def enqueue(
    db: AsyncSession,
    kind: str,
    payload: dict[str, Any],
    session_id: uuid.UUID | None,
    max_attempts: int,
    idempotency_key: str | None = None,
) -> Job:
    """Add a job in the caller's transaction: the job exists if and only if the work it describes does."""
    job = Job(
        kind=kind,
        payload=payload,
        session_id=session_id,
        max_attempts=max_attempts,
        idempotency_key=idempotency_key,
    )
    db.add(job)
    await db.flush()
    return job


# A queued job, or a running one whose lease ran out, is claimable. SKIP LOCKED lets workers claim at once.
_CLAIM = text(
    """
    UPDATE jobs SET status = 'running', locked_by = :worker, fence = fence + 1, attempts = attempts + 1,
           lease_until = now() + make_interval(secs => :lease),
           started_at = COALESCE(started_at, now())
    WHERE id = (
        SELECT id FROM jobs
        WHERE (status = 'queued' OR (status = 'running' AND lease_until < now()))
          AND attempts < max_attempts
        ORDER BY created_at
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    )
    RETURNING id, kind, payload, session_id, fence, attempts, max_attempts
    """
)

# A job that lost its lease with no attempts left is finished as interrupted, not retried forever.
_REAP = text(
    """
    UPDATE jobs SET status = 'failed', last_error = 'interrupted: attempts exhausted', finished_at = now(),
           locked_by = NULL
    WHERE status = 'running' AND lease_until < now() AND attempts >= max_attempts
    RETURNING id, kind, payload, session_id
    """
)


async def claim(worker: str, lease_seconds: float) -> Claimed | None:
    async with get_sessionmaker()() as db:
        row = (await db.execute(_CLAIM, {"worker": worker, "lease": lease_seconds})).first()
        await db.commit()
    if row is None:
        return None
    return Claimed(row[0], row[1], dict(row[2]), row[3], row[4], row[5], row[6])


async def reap_exhausted() -> list[tuple[uuid.UUID, str, dict[str, Any], uuid.UUID | None]]:
    async with get_sessionmaker()() as db:
        rows = (await db.execute(_REAP)).all()
        await db.commit()
    return [(r[0], r[1], dict(r[2]), r[3]) for r in rows]


async def heartbeat(job_id: uuid.UUID, fence: int, lease_seconds: float) -> bool:
    """Extend the lease. False means the lease was lost: stop, someone else owns the job now."""
    async with get_sessionmaker()() as db:
        result = await db.execute(
            text(
                "UPDATE jobs SET lease_until = now() + make_interval(secs => :lease) "
                "WHERE id = :id AND fence = :fence AND status = 'running'"
            ),
            {"id": job_id, "fence": fence, "lease": lease_seconds},
        )
        await db.commit()
    return bool(result.rowcount)  # type: ignore[attr-defined]


async def complete(job_id: uuid.UUID, fence: int, error: str | None = None) -> bool:
    """Record the outcome only while this worker still holds the fence."""
    async with get_sessionmaker()() as db:
        result = await db.execute(
            text(
                "UPDATE jobs SET status = :status, last_error = :error, finished_at = now(), "
                "locked_by = NULL "
                "WHERE id = :id AND fence = :fence AND status = 'running'"
            ),
            {"id": job_id, "fence": fence, "status": "failed" if error else "succeeded", "error": error},
        )
        await db.commit()
    return bool(result.rowcount)  # type: ignore[attr-defined]


MAX_FREE_RELEASES = 5


async def release(job_id: uuid.UUID, fence: int) -> None:
    """Hand a job back unfinished (shutdown). The attempt is given back for the first few releases only, so a
    job that always outlives the drain window cannot be kept alive forever by rolling restarts."""
    async with get_sessionmaker()() as db:
        await db.execute(
            text(
                "UPDATE jobs SET status = 'queued', locked_by = NULL, lease_until = NULL, "
                "releases = releases + 1, "
                "attempts = CASE WHEN releases < :free THEN GREATEST(attempts - 1, 0) ELSE attempts END "
                "WHERE id = :id AND fence = :fence AND status = 'running'"
            ),
            {"id": job_id, "fence": fence, "free": MAX_FREE_RELEASES},
        )
        await db.commit()


async def holds(db: AsyncSession, job_id: uuid.UUID, fence: int) -> bool:
    """Inside the caller's transaction: does this worker still own the job? The row is locked until the
    transaction ends, so a replacement worker cannot take over between the check and the write."""
    row = (
        await db.execute(
            text("SELECT 1 FROM jobs WHERE id = :id AND fence = :fence AND status = 'running' FOR UPDATE"),
            {"id": job_id, "fence": fence},
        )
    ).first()
    return row is not None


async def retry_or_fail(job: Claimed, error: str) -> bool:
    """A handler raised. Put the job back for another attempt while attempts remain; returns False when they
    are used up (the job is then failed, and the caller finishes its records)."""
    async with get_sessionmaker()() as db:
        result = await db.execute(
            text(
                "UPDATE jobs SET status = CASE WHEN attempts < max_attempts THEN 'queued' ELSE 'failed' END, "
                "last_error = :error, locked_by = NULL, lease_until = NULL, "
                "finished_at = CASE WHEN attempts < max_attempts THEN NULL ELSE now() END "
                "WHERE id = :id AND fence = :fence AND status = 'running' RETURNING status"
            ),
            {"id": job.id, "fence": job.fence, "error": error},
        )
        row = result.first()
        await db.commit()
    return row is not None and row[0] == "queued"
