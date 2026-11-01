"""The single-service demo serves only public assets and leaves the API in charge of /api."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture
def web_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    public = tmp_path / "public"
    public.mkdir()
    (public / "index.html").write_text("<!doctype html><title>PolicyPilot demo</title>")
    (public / "app.js").write_text("console.log('PolicyPilot')")
    (tmp_path / ".env").write_text("LLM_API_KEY=never-publish-this")
    monkeypatch.setenv("FRONTEND_DIST_DIR", str(public))
    get_settings.cache_clear()
    yield TestClient(create_app())
    get_settings.cache_clear()


def test_serves_the_built_frontend_and_assets(web_client: TestClient) -> None:
    response = web_client.get("/")
    assert response.status_code == 200
    assert "<title>PolicyPilot demo</title>" in response.text
    assert "text/html" in response.headers["content-type"]
    assert web_client.get("/app.js").text == "console.log('PolicyPilot')"


def test_api_routes_take_precedence_over_the_frontend(web_client: TestClient) -> None:
    response = web_client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert web_client.get("/api/v1/not-a-route").status_code == 404


@pytest.mark.parametrize("path", ["/.env", "/%2e%2e/.env", "/backend/app/config.py", "/missing.js"])
def test_private_or_missing_files_are_not_served(web_client: TestClient, path: str) -> None:
    response = web_client.get(path)
    assert response.status_code == 404
    assert "never-publish-this" not in response.text


def test_separate_api_keeps_static_serving_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FRONTEND_DIST_DIR", raising=False)
    get_settings.cache_clear()
    try:
        assert TestClient(create_app()).get("/").status_code == 404
    finally:
        get_settings.cache_clear()
