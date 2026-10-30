import pytest
from fastapi.testclient import TestClient

from app.agent.prompts import PROMPT_VERSION
from app.config import get_settings
from app.main import create_app


def test_run_configuration_is_public_and_contains_no_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "sk-or-v1-supersecret")
    monkeypatch.setenv("POSTGRES_PASSWORD", "hunter2")
    monkeypatch.setenv("DEMO_PASSCODE", "letmein")
    get_settings.cache_clear()
    try:
        body = TestClient(create_app()).get("/api/v1/config")
    finally:
        get_settings.cache_clear()
    assert body.status_code == 200
    data = body.json()
    assert data["model"]["prompt_version"] == PROMPT_VERSION
    assert data["retrieval"]["chunk_tokens"] == 200 and data["retrieval"]["chunk_overlap_tokens"] == 30
    assert data["agent_limits"]["max_tool_calls"] == 6
    assert data["protections"]["passcode_required"] is True
    text = body.text
    assert "supersecret" not in text and "hunter2" not in text and "letmein" not in text
