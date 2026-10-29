"""corpus_version: bumped whenever the searchable corpus changes. Durable in Postgres, mirrored in Redis.

Search cache keys include the version (docs/adr/0004), so a bump makes every old entry unreachable.
"""

import contextlib

from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppState
from app.state.redis import get_redis

KEY = "corpus_version"
REDIS_KEY = "corpus:version"


async def bump_corpus_version(db: AsyncSession) -> int:
    stmt = (
        insert(AppState)
        .values(key=KEY, value=1)
        .on_conflict_do_update(index_elements=[AppState.key], set_={"value": AppState.value + 1})
        .returning(AppState.value)
    )
    version = int((await db.execute(stmt)).scalar_one())
    with contextlib.suppress(RedisError, OSError):  # Postgres is the source of truth.
        await get_redis().set(REDIS_KEY, version)
    return version


async def get_corpus_version(db: AsyncSession) -> int:
    try:
        cached = await get_redis().get(REDIS_KEY)
        if cached is not None:
            return int(cached)
    except (RedisError, OSError):
        pass
    value = (await db.execute(select(AppState.value).where(AppState.key == KEY))).scalar_one_or_none()
    return int(value or 0)
