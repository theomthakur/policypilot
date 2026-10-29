"""Readiness against real Postgres and Redis. Skipped unless INTEGRATION=1 (CI sets it with service containers)."""

import os

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(os.getenv("INTEGRATION") != "1", reason="needs Postgres and Redis")


def test_ready_ok_with_real_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import get_settings
    from app.main import create_app

    monkeypatch.setenv("LLM_PROVIDER", "fake")
    get_settings.cache_clear()
    body = TestClient(create_app()).get("/api/v1/health/ready").json()
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["migrations"] == "ok"
    assert body["checks"]["redis"] == "ok"
    assert body["status"] == "ok"
    get_settings.cache_clear()
