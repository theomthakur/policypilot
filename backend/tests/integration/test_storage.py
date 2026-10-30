"""Uploads in an S3-compatible bucket: the API stores the PDF, a worker with no shared disk reads it back, and
the viewer download comes from the bucket. The bucket is a local S3 emulator (moto) unless S3_TEST_ENDPOINT
points at a real S3-compatible server (the run in docs/deployment-evidence used SeaweedFS)."""

import os
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.integration.test_ingestion_api import POLICY_PAGES


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def bucket() -> Iterator[str]:
    if os.environ.get("S3_TEST_ENDPOINT"):
        yield os.environ["S3_TEST_ENDPOINT"]
        return
    port = _free_port()
    server = subprocess.Popen(
        [str(Path(sys.executable).parent / "moto_server"), "-p", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(100):
        try:
            httpx.get(f"http://127.0.0.1:{port}/moto-api/", timeout=0.5)
            break
        except httpx.HTTPError:
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.terminate()
    server.wait(timeout=10)


def test_upload_is_stored_in_the_bucket_ingested_from_it_and_served_from_it(
    monkeypatch: pytest.MonkeyPatch, bucket: str, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.main import create_app
    from tests.integration.conftest import clear_caches, new_session

    for key, value in {
        "STORAGE_BACKEND": "s3",
        "S3_ENDPOINT": bucket,
        "S3_ACCESS_KEY": os.environ.get("S3_TEST_ACCESS_KEY", "test"),
        "S3_SECRET_KEY": os.environ.get("S3_TEST_SECRET_KEY", "test"),
        "S3_BUCKET": "uploads-test",
        "UPLOAD_DIR": str(tmp_path / "no-local-disk-is-used"),
    }.items():
        monkeypatch.setenv(key, value)
    clear_caches()
    pdf = make_pdf(POLICY_PAGES)
    with TestClient(create_app()) as client:
        new_session(client)
        uploaded = client.post(
            "/api/v1/documents", files={"file": ("policy.pdf", pdf.read_bytes(), "application/pdf")}
        )
        assert uploaded.status_code == 201
        body = uploaded.json()
        deadline = time.monotonic() + 30
        status = "queued"
        while time.monotonic() < deadline and status not in ("succeeded", "failed"):
            status = client.get(f"/api/v1/ingestion/{body['ingestion_run']['id']}").json()["status"]
            time.sleep(0.2)
        assert status == "succeeded"
        doc_id = body["document"]["id"]
        assert "10 Mbps" in client.get(f"/api/v1/documents/{doc_id}/pages/1").json()["text"]
        file = client.get(f"/api/v1/documents/{doc_id}/file")
        assert file.status_code == 200 and file.content.startswith(b"%PDF-")
        assert file.content == pdf.read_bytes()
        assert not (tmp_path / "no-local-disk-is-used").exists()  # nothing was written to a local volume
