"""Shared Redis client. Every caller must tolerate Redis being down (docs/adr/0004)."""

import logging
from functools import lru_cache
from typing import Literal

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import get_settings

logger = logging.getLogger("policypilot.redis")


@lru_cache
def get_redis() -> "Redis[str]":
    return Redis.from_url(
        get_settings().redis_url, decode_responses=True, socket_timeout=0.5, socket_connect_timeout=0.5
    )


async def redis_status() -> Literal["ok", "down"]:
    try:
        await get_redis().ping()
    except (RedisError, OSError):
        return "down"
    return "ok"
