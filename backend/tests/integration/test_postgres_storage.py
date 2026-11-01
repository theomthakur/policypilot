"""An upload's original PDF survives losing the web service's entire local filesystem."""

import time
import uuid
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage import get_storage
from tests.integration.conftest import clear_caches, new_session
from tests.integration.test_ingestion_api import POLICY_PAGES


def test_postgres_storage_deletes_uploaded_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "postgres")
    clear_caches()
    storage = get_storage()
    key = f"delete-test-{uuid.uuid4().hex}.pdf"
    storage.put(key, b"temporary-pdf-bytes")
    assert storage.read(key) == b"temporary-pdf-bytes"
    storage.delete(key)
    assert storage.read(key) is None


def test_uploaded_pdf_survives_a_new_application_instance(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "postgres")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "unused-local-disk"))
    clear_caches()
    original = make_pdf(POLICY_PAGES).read_bytes()
    with TestClient(create_app()) as client:
        new_session(client)
        uploaded = client.post(
            "/api/v1/documents", files={"file": ("policy.pdf", original, "application/pdf")}
        )
        assert uploaded.status_code == 201
        body = uploaded.json()
        run_id = body["ingestion_run"]["id"]
        deadline = time.monotonic() + 30
        status = "queued"
        while time.monotonic() < deadline and status not in ("succeeded", "failed"):
            status = client.get(f"/api/v1/ingestion/{run_id}").json()["status"]
            time.sleep(0.1)
        assert status == "succeeded"
        document_id = body["document"]["id"]
        cookies = dict(client.cookies)
    assert not (tmp_path / "unused-local-disk").exists()

    clear_caches()
    with TestClient(create_app()) as restarted:
        restarted.cookies.update(cookies)
        download = restarted.get(f"/api/v1/documents/{document_id}/file")
        assert download.status_code == 200
        assert download.content == original
        assert "10 Mbps" in restarted.get(f"/api/v1/documents/{document_id}/pages/1").json()["text"]
    with TestClient(create_app()) as stranger:
        new_session(stranger)
        assert stranger.get(f"/api/v1/documents/{document_id}/file").status_code == 404
