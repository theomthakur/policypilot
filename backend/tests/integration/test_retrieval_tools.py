"""Hybrid search and the read-only tools against real Postgres and Redis."""

import asyncio
import uuid
from collections.abc import Callable
from pathlib import Path

from tests.integration.conftest import clear_caches

POLICY_A = [
    "1. Guest Network\n\nThe guest network is limited to 10 Mbps download and 2 Mbps upload "
    "for unregistered devices.",
    "2. Password Rotation\n\nUsers must change passwords every 90 days. "
    "Passwords must be at least 12 characters.",
]
POLICY_B = [
    "1. Remote Access\n\nVPN exceptions are approved by the Chief Information Security Officer only.",
    "2. Device Encryption\n\nPersonal laptops must use full disk encryption before connecting "
    "to research systems.",
]


def _run(coro):  # type: ignore[no-untyped-def]
    clear_caches()
    try:
        return asyncio.run(coro)
    finally:
        clear_caches()


def _load(make_pdf: Callable[..., Path], tmp_path: Path) -> None:
    from app.ingest.pipeline import ensure_corpus_loaded

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_pdf(POLICY_A, name="corpus/01-acceptable-use.pdf")
    make_pdf(POLICY_B, name="corpus/02-remote-work.pdf")
    assert _run(ensure_corpus_loaded(corpus)) == 2


def test_search_returns_the_right_page_and_flags_weak_results(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.config import get_settings
    from app.tools.contracts import SearchDocumentsInput
    from app.tools.impl import ToolContext, search_documents

    _load(make_pdf, tmp_path)

    async def go() -> tuple[dict, dict, dict]:
        ctx = ToolContext(get_settings(), None)
        hit = await search_documents(ctx, SearchDocumentsInput(query="guest wifi bandwidth limit mbps"))
        again = await search_documents(ctx, SearchDocumentsInput(query="guest wifi bandwidth limit mbps"))
        nothing = await search_documents(
            ctx, SearchDocumentsInput(query="reimbursement for home internet bills")
        )
        return hit.model_dump(), again.model_dump(), nothing.model_dump()

    hit, again, nothing = _run(go())
    top = hit["data"]["hits"][0]
    assert top["page"] == 1 and "Mbps" in top["excerpt"]
    assert (
        hit["data"]["cached"] is False and again["data"]["cached"] is True
    )  # Redis cache, same corpus version
    assert nothing["data"]["weak"] is True or nothing["status"] == "empty"


def test_cross_document_search_and_read_pages(make_pdf: Callable[..., Path], tmp_path: Path) -> None:
    from app.config import get_settings
    from app.tools.contracts import ListDocumentsInput, ReadDocumentPagesInput, SearchDocumentsInput
    from app.tools.impl import ToolContext, list_documents, read_document_pages, search_documents

    _load(make_pdf, tmp_path)

    async def go() -> tuple[dict, dict, dict]:
        ctx = ToolContext(get_settings(), None)
        docs = (await list_documents(ctx, ListDocumentsInput())).data or {}
        remote = next(
            d for d in docs["documents"] if "remote" in d["title"].lower() or "Remote" in d["title"]
        )
        found = await search_documents(ctx, SearchDocumentsInput(query="who approves VPN exceptions"))
        page = await read_document_pages(
            ctx,
            ReadDocumentPagesInput(document_id=uuid.UUID(remote["document_id"]), page_start=1, page_end=2),
        )
        bad = await read_document_pages(
            ctx,
            ReadDocumentPagesInput(document_id=uuid.UUID(remote["document_id"]), page_start=1, page_end=9),
        )
        return found.model_dump(), page.model_dump(), bad.model_dump()

    found, page, bad = _run(go())
    assert "Chief Information Security Officer" in found["data"]["hits"][0]["excerpt"]
    assert [p["page"] for p in page["data"]["pages"]] == [1, 2]
    assert bad["status"] == "error" and bad["error"]["code"] == "OUT_OF_RANGE"


def test_tools_validate_arguments_and_survive_faults(make_pdf: Callable[..., Path], tmp_path: Path) -> None:
    from app.config import get_settings
    from app.tools.impl import FaultInjector, ToolContext, run_tool

    _load(make_pdf, tmp_path)

    async def go() -> tuple[dict, dict, dict, dict]:
        settings = get_settings().model_copy(update={"agent_tool_timeout_s": 0.2})
        ctx = ToolContext(settings, None, FaultInjector("search_documents:timeout:1", True))
        invalid = await run_tool(ctx, "search_documents", {"query": "x"})
        timeout = await run_tool(ctx, "search_documents", {"query": "guest network limit"})
        recovered = await run_tool(ctx, "search_documents", {"query": "guest network limit"})
        unknown = await run_tool(ctx, "delete_everything", {})
        return invalid.model_dump(), timeout.model_dump(), recovered.model_dump(), unknown.model_dump()

    invalid, timeout, recovered, unknown = _run(go())
    assert invalid["error"]["code"] == "INVALID_ARGUMENT"
    assert timeout["error"]["code"] == "TIMEOUT" and timeout["error"]["retryable"] is True
    assert recovered["status"] == "ok"
    assert unknown["error"]["code"] == "INVALID_ARGUMENT"


def test_session_uploads_are_invisible_to_other_sessions(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.config import get_settings
    from app.db.models import Document, IngestionRun, Session
    from app.db.session import get_sessionmaker
    from app.ingest.pipeline import ingest_document
    from app.tools.contracts import SearchDocumentsInput
    from app.tools.impl import ToolContext, search_documents

    private = make_pdf(["Private Notes\n\nThe secret launch codename is Bluebird."], name="private.pdf")

    async def go() -> tuple[int, int, list[str]]:
        sid, other = uuid.uuid4(), uuid.uuid4()
        async with get_sessionmaker()() as db:
            db.add_all([Session(id=sid), Session(id=other)])
            await db.flush()
            doc = Document(
                title="private.pdf",
                filename="private.pdf",
                storage_name="p.pdf",
                sha256="a" * 64,
                source="upload",
                session_id=sid,
            )
            db.add(doc)
            await db.flush()
            run = IngestionRun(document_id=doc.id)
            db.add(run)
            await db.commit()
            ids = (doc.id, run.id)
        await ingest_document(ids[0], ids[1], private)
        query = SearchDocumentsInput(query="secret launch codename")
        mine = await search_documents(ToolContext(get_settings(), sid), query)
        theirs = await search_documents(ToolContext(get_settings(), other), query)
        hallucinated_filter = await search_documents(
            ToolContext(get_settings(), sid),
            SearchDocumentsInput(
                query="secret launch codename",
                document_ids=[uuid.UUID("00000000-0000-4000-8000-000000000000")],
            ),
        )
        return (
            len((mine.data or {}).get("hits", [])),
            len((theirs.data or {}).get("hits", [])),
            [hit["title"] for hit in (hallucinated_filter.data or {}).get("hits", [])],
        )

    mine, theirs, fallback_titles = _run(go())
    assert mine >= 1 and theirs == 0
    assert "Private Notes" in fallback_titles
