"""Per-client rate limit and daily LLM budget. Redis first; Postgres (turn totals) is the durable fallback."""

import contextlib
import time
from datetime import UTC, datetime

from redis.exceptions import RedisError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError
from app.config import get_settings
from app.db.models import Turn
from app.state.redis import get_redis

_local_hits: dict[str, list[float]] = {}  # only used while Redis is down


async def check_rate_limit(client_key: str) -> None:
    limit = get_settings().rate_limit_per_minute
    try:
        key = f"rl:{client_key}:{int(time.time() // 60)}"
        redis = get_redis()
        count = int(await redis.incr(key))
        if count == 1:
            await redis.expire(key, 70)
    except (RedisError, OSError):
        now = time.monotonic()
        hits = [t for t in _local_hits.get(client_key, []) if now - t < 60]
        hits.append(now)
        _local_hits[client_key] = hits
        count = len(hits)
    if count > limit:
        raise ApiError(429, "RATE_LIMITED", "Too many requests. Please wait a minute and try again.")


def _budget_key() -> str:
    return f"budget:{datetime.now(UTC):%Y-%m-%d}"


async def spent_today(db: AsyncSession) -> float:
    try:
        raw = await get_redis().get(_budget_key())
        if raw is not None:
            return float(raw)
    except (RedisError, OSError):
        pass
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    total = (
        await db.execute(
            select(func.coalesce(func.sum(Turn.totals["estimated_cost_usd"].as_float()), 0.0)).where(
                Turn.created_at >= start
            )
        )
    ).scalar_one()
    return float(total or 0.0)


async def budget_exhausted(db: AsyncSession) -> bool:
    return await spent_today(db) >= get_settings().daily_budget_usd


async def add_spend(cost_usd: float) -> None:
    if cost_usd <= 0:
        return
    with contextlib.suppress(RedisError, OSError):
        redis = get_redis()
        key = _budget_key()
        await redis.incrbyfloat(key, cost_usd)
        await redis.expire(key, 3 * 86_400)
