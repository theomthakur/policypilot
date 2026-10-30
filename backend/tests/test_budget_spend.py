import pytest

from app.state import limits


class _Redis:
    def __init__(self, value: str | None) -> None:
        self.value = value

    async def get(self, key: str) -> str | None:
        return self.value


class _Result:
    def __init__(self, total: float) -> None:
        self.total = total

    def scalar_one(self) -> float:
        return self.total


class _Db:
    def __init__(self, total: float) -> None:
        self.total = total

    async def execute(self, statement: object) -> _Result:
        return _Result(self.total)


@pytest.mark.parametrize(
    ("redis_value", "database_total", "expected"),
    [
        ("0.10", 0.70, 0.70),  # the Redis counter restarted from zero: Postgres is the truth
        (None, 0.70, 0.70),  # the key was evicted
        ("0.90", 0.70, 0.90),  # the counter is ahead of what has been committed so far
    ],
)
async def test_daily_spend_is_never_less_than_what_postgres_recorded(
    monkeypatch: pytest.MonkeyPatch, redis_value: str | None, database_total: float, expected: float
) -> None:
    monkeypatch.setattr(limits, "get_redis", lambda: _Redis(redis_value))
    assert await limits.spent_today(_Db(database_total)) == pytest.approx(expected)  # type: ignore[arg-type]
