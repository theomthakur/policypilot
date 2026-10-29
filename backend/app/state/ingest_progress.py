"""Ingestion progress in Redis for fast UI polling; Postgres keeps the durable record."""

import contextlib
import json
from typing import Any

from redis.exceptions import RedisError

from app.config import get_settings
from app.state.redis import get_redis


def _key(run_id: str) -> str:
    return f"ingest:{run_id}"


async def publish(run_id: str, progress: dict[str, Any]) -> None:
    ttl = get_settings().ingest_status_ttl_seconds
    with contextlib.suppress(RedisError, OSError):
        await get_redis().set(_key(run_id), json.dumps(progress), ex=ttl)


async def read(run_id: str) -> dict[str, Any] | None:
    try:
        raw = await get_redis().get(_key(run_id))
    except (RedisError, OSError):
        return None
    return json.loads(raw) if raw else None
