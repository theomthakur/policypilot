"""Worker loop: claim a job, run its handler under a heartbeat, record the result under the fence.

Run embedded in the API (default) or as its own process: `python -m app.jobs.worker`.
"""

import asyncio
import contextlib
import logging
import os
import socket
import uuid

from app.config import get_settings
from app.jobs import handlers, queue

logger = logging.getLogger("policypilot.jobs")


class Worker:
    def __init__(self, concurrency: int | None = None) -> None:
        self.settings = get_settings()
        self.concurrency = concurrency or self.settings.worker_concurrency
        self.name = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self._stopping = asyncio.Event()
        self._tasks: set[asyncio.Task[None]] = set()

    async def run(self) -> None:
        loops = [asyncio.create_task(self._loop(i)) for i in range(self.concurrency)]
        reaper = asyncio.create_task(self._reaper())
        await self._stopping.wait()
        reaper.cancel()
        await asyncio.gather(*loops, return_exceptions=True)
        with contextlib.suppress(asyncio.CancelledError):
            await reaper

    async def stop(self, drain_seconds: float = 20.0) -> None:
        """Stop claiming. Let running jobs finish for `drain_seconds`, then hand the rest back."""
        self._stopping.set()
        running = list(self._tasks)
        if running:
            _, pending = await asyncio.wait(running, timeout=drain_seconds)
            for task in pending:
                task.cancel()  # _run_one releases the job in its cancellation handler
            await asyncio.gather(*pending, return_exceptions=True)

    async def _reaper(self) -> None:
        while True:
            try:
                for job_id, kind, payload, session_id in await queue.reap_exhausted():
                    logger.warning("job interrupted", extra={"fields": {"job_id": str(job_id), "kind": kind}})
                    await handlers.on_interrupted(kind, payload, session_id)
            except Exception:
                logger.exception("reaper failed")
            await asyncio.sleep(max(1.0, self.settings.job_lease_seconds / 3))

    async def _loop(self, slot: int) -> None:
        while not self._stopping.is_set():
            try:
                job = await queue.claim(f"{self.name}/{slot}", self.settings.job_lease_seconds)
            except Exception:
                logger.exception("claim failed (database unavailable?)")
                await asyncio.sleep(1.0)
                continue
            if job is None:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(self._stopping.wait(), self.settings.worker_poll_interval_s)
                continue
            task = asyncio.create_task(self._run_one(job))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            await asyncio.wait({task})

    async def _run_one(self, job: queue.Claimed) -> None:
        handler = asyncio.create_task(handlers.handle(job))
        lost = asyncio.Event()
        beat = asyncio.create_task(self._heartbeat(job, handler, lost))
        try:
            await handler
            if not await queue.complete(job.id, job.fence):
                logger.warning("lost the lease before finishing", extra={"fields": {"job_id": str(job.id)}})
        except asyncio.CancelledError:
            if lost.is_set():  # another worker owns the job now: stop quietly, write nothing
                logger.warning(
                    "handler stopped after losing its lease", extra={"fields": {"job_id": str(job.id)}}
                )
                return
            handler.cancel()
            await queue.release(job.id, job.fence)
            raise
        except Exception as exc:
            logger.exception("job failed", extra={"fields": {"job_id": str(job.id)}})
            await self._after_failure(job, f"{type(exc).__name__}: {str(exc)[:300]}")
        finally:
            beat.cancel()

    async def _after_failure(self, job: queue.Claimed, error: str) -> None:
        """A handler raised (a database failover, a bad upload): retry after a short backoff while attempts
        remain, otherwise finish the job's own records so nothing stays 'running' forever."""
        await asyncio.sleep(min(2.0 * job.attempts, 10.0))
        try:
            if await queue.retry_or_fail(job, error):
                return
            await handlers.on_interrupted(job.kind, job.payload, job.session_id)
        except Exception:
            logger.exception("could not record the failure", extra={"fields": {"job_id": str(job.id)}})

    async def _heartbeat(
        self, job: queue.Claimed, handler: "asyncio.Task[None]", lost: asyncio.Event
    ) -> None:
        while True:
            await asyncio.sleep(self.settings.job_heartbeat_seconds)
            try:
                if not await queue.heartbeat(job.id, job.fence, self.settings.job_lease_seconds):
                    logger.warning("lease lost", extra={"fields": {"job_id": str(job.id)}})
                    lost.set()
                    handler.cancel()  # the work belongs to another worker now
                    return
            except Exception:
                logger.exception("heartbeat failed")


async def _main() -> None:
    from app.logging import configure_logging

    configure_logging(get_settings().log_level)
    worker = Worker()
    loop = asyncio.get_running_loop()
    import signal

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))
    await worker.run()


if __name__ == "__main__":
    asyncio.run(_main())
