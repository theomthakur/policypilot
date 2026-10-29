"""One browser session must never read or write another session's resources."""

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.integration.test_turns_api import _boot, _lookup_model, _send, _session_id, _wait

NIL = "00000000-0000-0000-0000-000000000000"


def _switch_to_new_session(client: TestClient) -> str:
    client.cookies.clear()
    assert client.post("/api/v1/sessions").status_code == 201
    return _session_id(client)


def test_another_sessions_cookie_cannot_read_or_write_a_session(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    with _boot(monkeypatch, _lookup_model(), make_pdf, tmp_path) as client:
        owner = _session_id(client)
        turn_id = _send(client, "What is the guest bandwidth limit?").json()["turn_id"]
        _wait(client, turn_id)
        assert client.get(f"/api/v1/sessions/{owner}").status_code == 200  # the owner still can

        _switch_to_new_session(client)
        assert client.get(f"/api/v1/sessions/{owner}").status_code == 404
        assert client.get(f"/api/v1/turns/{turn_id}").status_code == 404
        assert client.get(f"/api/v1/turns/{turn_id}/events").status_code == 404
        intruder = client.post(f"/api/v1/sessions/{owner}/messages", json={"content": "hi"})
        assert intruder.status_code == 404


def test_requests_without_any_cookie_get_the_same_404(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    with _boot(monkeypatch, _lookup_model(), make_pdf, tmp_path) as client:
        owner = _session_id(client)
        turn_id = _send(client, "What is the guest bandwidth limit?").json()["turn_id"]
        _wait(client, turn_id)
        client.cookies.clear()
        for path in (
            f"/api/v1/sessions/{owner}",
            f"/api/v1/turns/{turn_id}",
            f"/api/v1/turns/{turn_id}/events",
        ):
            response = client.get(path)
            assert response.status_code == 404 and response.json()["error"]["code"] == "NOT_FOUND"
        missing = client.get(f"/api/v1/turns/{NIL}")
        assert (
            missing.json() == client.get(f"/api/v1/turns/{turn_id}").json()
        )  # exists and missing look identical


def test_uploaded_document_and_its_ingestion_run_are_private_to_the_uploading_session(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel

    pdf = make_pdf(["1. Private\n\nCafeteria opens at nine every morning."], name="private.pdf")
    with _boot(monkeypatch, ScriptedModel([]), make_pdf, tmp_path) as client:
        uploaded = client.post(
            "/api/v1/documents", files={"file": ("private.pdf", pdf.read_bytes(), "application/pdf")}
        )
        assert uploaded.status_code == 201
        document_id = uploaded.json()["document"]["id"]
        run_id = uploaded.json()["ingestion_run"]["id"]
        assert client.get(f"/api/v1/ingestion/{run_id}").status_code == 200

        _switch_to_new_session(client)
        assert client.get(f"/api/v1/documents/{document_id}").status_code == 404
        assert client.get(f"/api/v1/documents/{document_id}/pages/1").status_code == 404
        assert client.get(f"/api/v1/ingestion/{run_id}").status_code == 404
        assert document_id not in {d["id"] for d in client.get("/api/v1/documents").json()["items"]}
