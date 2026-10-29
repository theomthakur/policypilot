"""Search result cache in Redis. Keys include the corpus version, so a corpus change makes old entries
unreachable (docs/adr/0004). If Redis is down, searches simply run uncached."""

import contextlib
import hashlib
import json
import uuid
from typing import Any

from redis.exceptions import RedisError

from app.config import get_settings
from app.state.redis import get_redis


def cache_key(
    corpus_version: int,
    session_id: uuid.UUID | None,
    query: str,
    document_ids: list[uuid.UUID],
    page_start: int | None,
    page_end: int | None,
    top_k: int,
) -> str:
    material = json.dumps(
        [str(session_id), query.strip().lower(), sorted(map(str, document_ids)), page_start, page_end, top_k]
    )
    digest = hashlib.sha256(material.encode()).hexdigest()[:32]
    return f"search:{corpus_version}:{digest}"


async def get_cached(key: str) -> dict[str, Any] | None:
    try:
        raw = await get_redis().get(key)
    except (RedisError, OSError):
        return None
    return json.loads(raw) if raw else None


async def set_cached(key: str, value: dict[str, Any]) -> None:
    with contextlib.suppress(RedisError, OSError):
        await get_redis().set(key, json.dumps(value), ex=get_settings().search_cache_ttl_seconds)
