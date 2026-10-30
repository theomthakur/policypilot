"""Liveness and readiness endpoints.

Readiness rules (see docs/adr/0004): the database and migrations must be up for `ok`;
Redis being down only degrades the service, it doesn't make it unready.
"""

from collections.abc import Awaitable, Callable
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])

CheckStatus = Literal["ok", "down"]
MigrationStatus = Literal["ok", "pending", "down"]


class ReadinessChecks(BaseModel):
    database: Literal["ok", "down"]
    migrations: Literal["ok", "pending", "down"]
    redis: Literal["ok", "down"]
    llm_config: Literal["ok", "missing"]


class Readiness(BaseModel):
    status: Literal["ok", "degraded", "down"]
    version: str
    checks: ReadinessChecks
    corpus_documents: int | None = None


async def _database_check() -> tuple[CheckStatus, MigrationStatus]:
    from app.db.health import database_status

    return await database_status()


async def _redis_check() -> CheckStatus:
    from app.state.redis import redis_status

    return await redis_status()


async def _corpus_count() -> int | None:
    from app.db.health import corpus_documents

    return await corpus_documents()


# Indirection so tests and later tasks can swap the checks without touching the routes.
database_check: Callable[[], Awaitable[tuple[CheckStatus, MigrationStatus]]] = _database_check
redis_check: Callable[[], Awaitable[CheckStatus]] = _redis_check
corpus_count: Callable[[], Awaitable[int | None]] = _corpus_count


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", response_model=Readiness)
async def ready(response: Response) -> Readiness:
    settings = get_settings()
    db, migrations = await database_check()
    redis = await redis_check()
    checks = ReadinessChecks(
        database=db,
        migrations=migrations,
        redis=redis,
        llm_config="ok" if settings.llm_configured else "missing",
    )
    if db != "ok" or migrations != "ok":
        status: Literal["ok", "degraded", "down"] = "down"
        response.status_code = 503
    elif redis != "ok" or checks.llm_config != "ok":
        status = "degraded"
    else:
        status = "ok"
    corpus = await corpus_count() if db == "ok" and migrations == "ok" else None
    return Readiness(status=status, version=settings.app_version, checks=checks, corpus_documents=corpus)
