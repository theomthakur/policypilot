import asyncio
import time
from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.integration.conftest import clear_caches, new_session

POLICY_PAGES = [
    "1. Guest Network\n\nThe guest network is limited to 10 Mbps download for unregistered devices.",
    "2. Passwords\n\nPasswords must be at least 14 characters. Multi-factor authentication is required.",
]


def _upload(client: TestClient, path: Path, name: str = "policy.pdf") -> dict:
    with path.open("rb") as fh:
        response = client.post("/api/v1/documents", files={"file": (name, fh, "application/pdf")})
    assert response.status_code in (200, 201), response.text
    body = response.json()
    deadline = time.monotonic() + 20  # ingestion is a background job now: wait for it to finish
    while time.monotonic() < deadline:
        status = client.get(f"/api/v1/ingestion/{body['ingestion_run']['id']}").json()["status"]
        if status in ("succeeded", "failed"):
            break
        time.sleep(0.1)
    return body  # type: ignore[no-any-return]


def test_upload_ingests_pages_and_page_bounded_chunks(
    client: TestClient, make_pdf: Callable[..., Path]
) -> None:
    new_session(client)
    body = _upload(client, make_pdf(POLICY_PAGES))
    doc_id = body["document"]["id"]

    run = client.get(f"/api/v1/ingestion/{body['ingestion_run']['id']}").json()
    assert run["status"] == "succeeded" and run["stage"] == "done"

    doc = client.get(f"/api/v1/documents/{doc_id}").json()
    assert doc["status"] == "ready" and doc["page_count"] == 2 and doc["source"] == "upload"

    page = client.get(f"/api/v1/documents/{doc_id}/pages/1").json()
    assert "10 Mbps" in page["text"]
    assert client.get(f"/api/v1/documents/{doc_id}/pages/3").status_code == 404

    from app.db.models import Chunk
    from app.db.session import get_sessionmaker

    async def chunk_pages() -> list[int]:
        async with get_sessionmaker()() as db:
            return list(
                (await db.execute(select(Chunk.page_number).where(Chunk.document_id == doc_id))).scalars()
            )

    clear_caches()
    assert set(asyncio.run(chunk_pages())) == {1, 2}


def test_duplicate_upload_returns_the_existing_document(
    client: TestClient, make_pdf: Callable[..., Path]
) -> None:
    new_session(client)
    path = make_pdf(POLICY_PAGES)
    first = _upload(client, path)
    second = _upload(client, path, name="renamed.pdf")
    assert second["duplicate"] is True
    assert second["document"]["id"] == first["document"]["id"]


def test_uploads_are_isolated_between_sessions(make_pdf: Callable[..., Path]) -> None:
    from app.main import create_app

    with TestClient(create_app()) as client:

        def session_cookie() -> dict[str, str]:
            client.cookies.clear()
            assert client.post("/api/v1/sessions").status_code == 201
            cookie = {"pp_session": client.cookies["pp_session"]}
            client.cookies.clear()
            return cookie

        alice, bob = session_cookie(), session_cookie()
        client.cookies.update(alice)
        doc_id = _upload(client, make_pdf(POLICY_PAGES))["document"]["id"]
        client.cookies.clear()

        client.cookies.update(bob)
        assert client.get(f"/api/v1/documents/{doc_id}").status_code == 404
        assert all(d["id"] != doc_id for d in client.get("/api/v1/documents").json()["items"])
        client.cookies.clear()

        client.cookies.update(alice)
        assert any(d["id"] == doc_id for d in client.get("/api/v1/documents").json()["items"])


def test_rejects_non_pdf_and_requires_a_session(client: TestClient, tmp_path: Path) -> None:
    fake = tmp_path / "notes.pdf"
    fake.write_text("hello")
    with fake.open("rb") as fh:
        no_session = client.post("/api/v1/documents", files={"file": ("notes.pdf", fh, "application/pdf")})
    assert no_session.status_code == 400
    new_session(client)
    with fake.open("rb") as fh:
        response = client.post("/api/v1/documents", files={"file": ("notes.pdf", fh, "application/pdf")})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_PDF"


def test_pdf_without_text_fails_cleanly(client: TestClient, make_pdf: Callable[..., Path]) -> None:
    new_session(client)
    body = _upload(client, make_pdf(["", ""]))
    doc = client.get(f"/api/v1/documents/{body['document']['id']}").json()
    assert doc["status"] == "failed"
    assert "No text layer" in doc["error"]


def test_corpus_autoload_is_idempotent_and_bumps_the_version(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.db.models import Document
    from app.db.session import get_sessionmaker
    from app.ingest.pipeline import ensure_corpus_loaded

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_pdf(POLICY_PAGES, name="corpus/01-policy.pdf")

    assert asyncio.run(ensure_corpus_loaded(corpus)) == 1
    clear_caches()
    assert asyncio.run(ensure_corpus_loaded(corpus)) == 0
    clear_caches()

    async def corpus_docs() -> int:
        async with get_sessionmaker()() as db:
            q = (
                select(func.count())
                .select_from(Document)
                .where(Document.source == "corpus", Document.status == "ready")
            )
            return int((await db.execute(q)).scalar_one())

    assert asyncio.run(corpus_docs()) == 1
    clear_caches()
    from app.main import create_app

    with TestClient(create_app()) as c:
        listing = c.get("/api/v1/documents").json()
    assert listing["corpus_version"] >= 1
    assert listing["items"][0]["source"] == "corpus"


def test_original_pdf_is_served_inline_to_the_session_that_may_see_it(
    client: TestClient, make_pdf: Callable[..., Path]
) -> None:
    assert client.post("/api/v1/sessions").status_code == 201
    path = make_pdf(POLICY_PAGES)
    body = _upload(client, path)
    document_id = body["document"]["id"]

    response = client.get(f"/api/v1/documents/{document_id}/file")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline")
    assert response.content == path.read_bytes()

    client.cookies.clear()
    assert client.post("/api/v1/sessions").status_code == 201  # a different session
    assert client.get(f"/api/v1/documents/{document_id}/file").status_code == 404
