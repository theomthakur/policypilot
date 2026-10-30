"""Durable jobs: leases, fencing, crash recovery, duplicate delivery, idempotency, shutdown, seeding lock."""

import asyncio
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select, text

from tests.integration.conftest import clear_caches
from tests.integration.test_turns_api import _boot, _lookup_model, _send, _session_id, _wait


def run(coro: Any) -> Any:
    clear_caches()
    try:
        return asyncio.run(coro)
    finally:
        clear_caches()


async def _new_job(
    max_attempts: int = 3, kind: str = "ingest", payload: dict[str, Any] | None = None
) -> uuid.UUID:
    from app.db.session import get_sessionmaker
    from app.jobs import queue

    async with get_sessionmaker()() as db:
        job = await queue.enqueue(db, kind, payload or {"x": 1}, None, max_attempts)
        await db.commit()
        return job.id


async def _expire(job_id: uuid.UUID) -> None:
    from app.db.session import get_sessionmaker

    async with get_sessionmaker()() as db:
        await db.execute(
            text("UPDATE jobs SET lease_until = now() - interval '1 second' WHERE id = :i"), {"i": job_id}
        )
        await db.commit()


async def _row(job_id: uuid.UUID) -> Any:
    from app.db.models import Job
    from app.db.session import get_sessionmaker

    async with get_sessionmaker()() as db:
        job = await db.get(Job, job_id)
        assert job is not None
        await db.refresh(job)
        return job


def test_a_claimed_job_is_invisible_to_other_workers_until_its_lease_runs_out() -> None:
    from app.jobs import queue

    async def go() -> None:
        job_id = await _new_job()
        first = await queue.claim("worker-a", 60)
        assert first is not None and first.id == job_id and first.fence == 1
        assert await queue.claim("worker-b", 60) is None  # leased: nobody else can take it
        await _expire(job_id)
        second = await queue.claim("worker-b", 60)
        assert second is not None and second.id == job_id and second.fence == 2 and second.attempts == 2

    run(go())


def test_a_stalled_worker_cannot_overwrite_its_replacements_result() -> None:
    from app.jobs import queue

    async def go() -> None:
        job_id = await _new_job()
        stale = await queue.claim("worker-a", 60)
        await _expire(job_id)
        fresh = await queue.claim("worker-b", 60)
        assert stale is not None and fresh is not None
        assert await queue.heartbeat(job_id, stale.fence, 60) is False  # it learns it lost the job
        assert await queue.complete(job_id, stale.fence, error="late failure") is False  # and cannot record
        assert await queue.complete(job_id, fresh.fence) is True
        job = await _row(job_id)
        assert job.status == "succeeded" and job.last_error is None

    run(go())


def test_a_job_that_keeps_crashing_ends_as_interrupted_not_forever_running() -> None:
    from app.jobs import queue

    async def go() -> None:
        job_id = await _new_job(max_attempts=2)
        for attempt in (1, 2):
            claimed = await queue.claim("w", 60)
            assert claimed is not None and claimed.attempts == attempt
            await _expire(job_id)  # the worker died
        assert await queue.claim("w", 60) is None  # no attempts left
        reaped = await queue.reap_exhausted()
        assert [r[0] for r in reaped] == [job_id]
        job = await _row(job_id)
        assert job.status == "failed" and "interrupted" in job.last_error

    run(go())


def test_shutdown_hands_a_running_job_back_without_using_up_an_attempt() -> None:
    from app.jobs import handlers
    from app.jobs.worker import Worker

    async def go() -> None:
        job_id = await _new_job()
        started = asyncio.Event()

        async def slow(_: Any) -> None:
            started.set()
            await asyncio.sleep(30)

        original = handlers.handle
        handlers.handle = slow  # type: ignore[assignment]
        try:
            worker = Worker(concurrency=1)
            task = asyncio.create_task(worker.run())
            await asyncio.wait_for(started.wait(), 5)
            await worker.stop(drain_seconds=0.2)
            await task
        finally:
            handlers.handle = original  # type: ignore[assignment]
        job = await _row(job_id)
        assert job.status == "queued" and job.attempts == 0 and job.locked_by is None

    run(go())


def test_duplicate_delivery_of_a_finished_turn_changes_nothing(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    with _boot(monkeypatch, _lookup_model(), make_pdf, tmp_path) as client:
        turn_id = _send(client, "What is the guest bandwidth limit?").json()["turn_id"]
        before = _wait(client, turn_id)
        assert before["status"] == "completed"
        session_id = _session_id(client)

    from app.turns.service import run_turn

    async def again() -> tuple[int, int]:
        from app.db.models import Citation, TraceEvent
        from app.db.session import get_sessionmaker

        await run_turn(uuid.UUID(turn_id), uuid.UUID(session_id), None, None)  # delivered a second time
        async with get_sessionmaker()() as db:
            events = (await db.execute(select(func.count()).select_from(TraceEvent))).scalar_one()
            cites = (await db.execute(select(func.count()).select_from(Citation))).scalar_one()
            return int(events), int(cites)

    events_after, citations_after = run(again())
    assert events_after == len(before["events"]) and citations_after == len(before["answer"]["citations"])


def test_a_turn_whose_first_attempt_crashed_resumes_with_a_visible_marker(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    # WORKER_EMBEDDED=false: the API accepts the question and records the job, but no worker is alive yet.
    with _boot(monkeypatch, _lookup_model(), make_pdf, tmp_path, WORKER_EMBEDDED="false") as client:
        turn_id = _send(client, "What is the guest bandwidth limit?").json()["turn_id"]
        assert client.get(f"/api/v1/turns/{turn_id}").json()["status"] == "running"  # persisted, waiting
        session_id = _session_id(client)

    async def crash_then_recover() -> list[dict[str, Any]]:
        from app.db.models import TraceEvent
        from app.db.session import get_sessionmaker
        from app.turns.service import run_turn

        async with get_sessionmaker()() as db:  # the first attempt got as far as one trace event, then died
            db.add(
                TraceEvent(turn_id=uuid.UUID(turn_id), seq=0, type="turn_started", payload={"status": "info"})
            )
            await db.commit()
        monkeypatch.setattr("app.turns.service.get_model", lambda: _lookup_model())
        await run_turn(uuid.UUID(turn_id), uuid.UUID(session_id), None, None)
        async with get_sessionmaker()() as db:
            rows = (
                (
                    await db.execute(
                        select(TraceEvent)
                        .where(TraceEvent.turn_id == uuid.UUID(turn_id))
                        .order_by(TraceEvent.seq)
                    )
                )
                .scalars()
                .all()
            )
            return [{"seq": r.seq, "type": r.type} for r in rows]

    events = run(crash_then_recover())
    assert [e["seq"] for e in events] == list(range(len(events)))  # no gaps, no overwrites
    assert events[1]["type"] == "turn_resumed" and events[-1]["type"] == "turn_completed"


def test_a_retried_request_with_the_same_idempotency_key_makes_one_turn(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    with _boot(monkeypatch, _lookup_model(), make_pdf, tmp_path) as client:
        session_id = _session_id(client)
        headers = {"Idempotency-Key": "abc-123"}
        body = {"content": "What is the guest bandwidth limit?"}
        first = client.post(f"/api/v1/sessions/{session_id}/messages", json=body, headers=headers)
        second = client.post(f"/api/v1/sessions/{session_id}/messages", json=body, headers=headers)
        assert first.status_code == second.status_code == 202
        assert first.json()["turn_id"] == second.json()["turn_id"]
        _wait(client, first.json()["turn_id"])

    async def counts() -> tuple[int, int]:
        from app.db.models import Job, Turn
        from app.db.session import get_sessionmaker

        async with get_sessionmaker()() as db:
            turns = (await db.execute(select(func.count()).select_from(Turn))).scalar_one()
            jobs = (await db.execute(select(func.count()).select_from(Job))).scalar_one()
            return int(turns), int(jobs)

    assert run(counts()) == (1, 1)


def test_an_interrupted_turn_ends_with_an_honest_failed_answer(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    with _boot(monkeypatch, _lookup_model(), make_pdf, tmp_path, WORKER_EMBEDDED="false") as client:
        turn_id = _send(client, "What is the guest bandwidth limit?").json()["turn_id"]

    async def interrupt() -> None:
        from app.turns.service import mark_interrupted

        await mark_interrupted(uuid.UUID(turn_id))

    run(interrupt())

    # Read the stored turn directly: it is no longer 'running'.
    async def stored() -> tuple[str, str]:
        from app.db.models import Turn
        from app.db.session import get_sessionmaker

        async with get_sessionmaker()() as db:
            turn = await db.get(Turn, uuid.UUID(turn_id))
            assert turn is not None and turn.answer is not None
            return turn.status, str(turn.answer["summary"])

    status, summary = run(stored())
    assert status == "failed" and "interrupted" in summary


def test_only_one_instance_seeds_the_corpus_at_a_time(tmp_path: Path) -> None:
    from app.db.session import get_engine
    from app.main import SEED_LOCK, _load_all

    async def go() -> int:
        async with get_engine().connect() as holder:
            await holder.execute(text("SELECT pg_advisory_lock(:k)"), {"k": SEED_LOCK})
            try:
                return await _load_all(tmp_path, "")  # another instance holds the lock: skip, do not race
            finally:
                await holder.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": SEED_LOCK})

    assert run(go()) == 0
