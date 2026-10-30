from typing import Literal

import pytest
from fastapi.testclient import TestClient

from app.api import health
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _set_checks(
    monkeypatch: pytest.MonkeyPatch,
    db: Literal["ok", "down"],
    migrations: Literal["ok", "pending", "down"],
    redis: Literal["ok", "down"],
) -> None:
    async def fake_db() -> tuple[Literal["ok", "down"], Literal["ok", "pending", "down"]]:
        return db, migrations

    async def fake_redis() -> Literal["ok", "down"]:
        return redis

    async def fake_corpus() -> int | None:
        return 10

    monkeypatch.setattr(health, "database_check", fake_db)
    monkeypatch.setattr(health, "redis_check", fake_redis)
    monkeypatch.setattr(health, "corpus_count", fake_corpus)


def test_live_is_always_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]


def test_ready_ok_when_everything_is_up(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    health.get_settings.cache_clear()
    _set_checks(monkeypatch, "ok", "ok", "ok")
    body = client.get("/api/v1/health/ready").json()
    assert body["status"] == "ok" and body["corpus_documents"] == 10
    health.get_settings.cache_clear()


def test_redis_down_only_degrades(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    health.get_settings.cache_clear()
    _set_checks(monkeypatch, "ok", "ok", "down")
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["redis"] == "down"
    health.get_settings.cache_clear()


def test_database_down_is_not_ready(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_checks(monkeypatch, "down", "down", "ok")
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "down" and response.json()["corpus_documents"] is None


def test_pending_migrations_are_not_ready(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_checks(monkeypatch, "ok", "pending", "ok")
    assert client.get("/api/v1/health/ready").status_code == 503
