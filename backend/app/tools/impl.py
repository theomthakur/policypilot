"""Read-only tool implementations. Tools only see documents visible to the session (REQ-F6, REQ-F7)."""

import asyncio
import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import Document, DocumentPage, Session
from app.db.session import get_sessionmaker
from app.retrieval import cache as search_cache
from app.retrieval.hybrid import SearchResult, hybrid_search
from app.state.corpus import get_corpus_version
from app.tools.contracts import (
    ErrorCode,
    GetDocumentOutlineInput,
    ListDocumentsInput,
    ReadDocumentPagesInput,
    SearchDocumentsInput,
    ToolError,
    ToolResult,
)

_HEADING = re.compile(r"^\d+(\.\d+)*\.?\s+\S.{0,100}$")


class FaultInjector:
    """Test-only: make a tool fail or time out N times (e.g. 'search_documents:timeout:1')."""

    def __init__(self, spec: str | None, enabled: bool) -> None:
        self.remaining: dict[str, tuple[str, int]] = {}
        if spec and enabled:
            tool, kind, count = [*spec.split(":"), "timeout", "1"][:3]
            self.remaining[tool] = (kind, int(count))

    def take(self, tool: str) -> str | None:
        entry = self.remaining.get(tool)
        if not entry or entry[1] <= 0:
            return None
        self.remaining[tool] = (entry[0], entry[1] - 1)
        return entry[0]


@dataclass
class ToolContext:
    settings: Settings
    session_id: uuid.UUID | None
    faults: FaultInjector = field(default_factory=lambda: FaultInjector(None, False))


def _error(code: ErrorCode, message: str, retryable: bool = False) -> ToolResult:
    return ToolResult(
        status="error",
        error=ToolError(code=code, message=message, retryable=retryable),
        summary=f"{code}: {message}"[:300],
    )


def _visible(session_id: uuid.UUID | None, account_library: bool) -> Any:
    if session_id is None:
        return Document.session_id.is_(None)
    if account_library:
        owner_id = select(Session.owner_user_id).where(Session.id == session_id).scalar_subquery()
        owner_sessions = select(Session.id).where(Session.owner_user_id == owner_id)
        return or_(Document.session_id.is_(None), Document.session_id.in_(owner_sessions))
    return or_(Document.session_id.is_(None), Document.session_id == session_id)


async def _visible_doc(
    db: AsyncSession, document_id: uuid.UUID, session_id: uuid.UUID | None, account_library: bool
) -> Document | None:
    query = select(Document).where(Document.id == document_id, _visible(session_id, account_library))
    return (await db.execute(query)).scalar_one_or_none()


async def list_documents(ctx: ToolContext, args: ListDocumentsInput) -> ToolResult:
    async with get_sessionmaker()() as db:
        query = (
            select(Document)
            .where(_visible(ctx.session_id, ctx.settings.auth_mode != "off"))
            .order_by(Document.filename)
            .limit(args.limit)
        )
        if args.status == "ready":
            query = query.where(Document.status == "ready")
        if args.title_contains:
            query = query.where(Document.title.ilike(f"%{args.title_contains}%"))
        docs = (await db.execute(query)).scalars().all()
        version = await get_corpus_version(db)
    if not docs:
        return ToolResult(
            status="empty",
            data={"documents": [], "corpus_version": version},
            summary="No documents match.",
            suggestion="Drop the title filter.",
        )
    return ToolResult(
        status="ok",
        data={
            "documents": [
                {
                    "document_id": str(d.id),
                    "title": d.title,
                    "page_count": d.page_count,
                    "status": d.status,
                    "source": d.source,
                    "authority": d.authority,
                    "effective_date": d.effective_date,
                    "version": d.version,
                }
                for d in docs
            ],
            "corpus_version": version,
        },
        summary=f"{len(docs)} documents.",
    )


def _result_to_data(result: SearchResult, version: int, cached: bool) -> dict[str, Any]:
    return {
        "hits": [
            {
                "chunk_id": str(h.chunk_id),
                "document_id": str(h.document_id),
                "title": h.title,
                "page": h.page,
                "section": h.section,
                "excerpt": h.excerpt,
                "vector_rank": h.vector_rank,
                "text_rank": h.text_rank,
                "fused_score": h.fused_score,
                "authority": h.authority,
                "effective_date": h.effective_date,
                "version": h.version,
                "related_version": h.related,
                "supersedes": list(h.supersedes),
            }
            for h in result.hits
        ],
        "weak": result.weak,
        "off_topic": result.off_topic,
        "top_score": result.top_score,
        "corpus_version": version,
        "cached": cached,
    }


async def search_documents(ctx: ToolContext, args: SearchDocumentsInput) -> ToolResult:
    async with get_sessionmaker()() as db:
        version = await get_corpus_version(db)
        # A model may hallucinate UUID-looking document IDs. Filters are only useful when at least one
        # requested document is real, ready, and visible to this session. Otherwise search the whole
        # visible library rather than turning a valid question about a private upload into an empty result.
        document_ids = args.document_ids
        if document_ids:
            document_ids = list(
                (
                    await db.execute(
                        select(Document.id).where(
                            Document.id.in_(document_ids),
                            Document.status == "ready",
                            _visible(ctx.session_id, ctx.settings.auth_mode != "off"),
                        )
                    )
                ).scalars()
            )
        key = search_cache.cache_key(
            version, ctx.session_id, args.query, document_ids, args.page_start, args.page_end, args.top_k
        )
        data = await search_cache.get_cached(key)
        if data is not None:
            data = {**data, "cached": True}
        else:
            result = await hybrid_search(
                db,
                args.query,
                ctx.session_id,
                document_ids,
                args.page_start,
                args.page_end,
                args.top_k,
                account_library=ctx.settings.auth_mode != "off",
            )
            data = _result_to_data(result, version, cached=False)
            await search_cache.set_cached(key, data)
    hits = data["hits"]
    if not hits:
        return ToolResult(
            status="empty",
            data=data,
            summary="No results.",
            suggestion="Rephrase with terms the policies themselves would use, or list_documents.",
        )
    pages = sorted({(h["title"], h["page"]) for h in hits})[:4]
    label = ", ".join(f"{t} p.{p}" for t, p in pages)
    weak = " (weak)" if data["weak"] else ""
    return ToolResult(
        status="ok",
        data=data,
        summary=f"{len(hits)} hits{weak}: {label}"[:300],
        suggestion="Results look weak: rephrase using the documents' vocabulary." if data["weak"] else None,
    )


async def read_document_pages(ctx: ToolContext, args: ReadDocumentPagesInput) -> ToolResult:
    end = args.page_end or args.page_start
    if end < args.page_start or end - args.page_start + 1 > ctx.settings.agent_max_pages_per_read:
        return _error(
            "OUT_OF_RANGE", f"Read at most {ctx.settings.agent_max_pages_per_read} consecutive pages."
        )
    async with get_sessionmaker()() as db:
        doc = (
            await db.execute(
                select(Document).where(
                    Document.id == args.document_id,
                    _visible(ctx.session_id, ctx.settings.auth_mode != "off"),
                )
            )
        ).scalar_one_or_none()
        if doc is None:
            return _error("DOCUMENT_NOT_FOUND", "No such document.")
        if doc.status != "ready":
            return _error("DOCUMENT_NOT_READY", "The document is still being processed.", retryable=True)
        if end > doc.page_count:
            return _error("OUT_OF_RANGE", f"The document has {doc.page_count} pages.")
        rows = (
            (
                await db.execute(
                    select(DocumentPage)
                    .where(
                        DocumentPage.document_id == doc.id,
                        DocumentPage.page_number.between(args.page_start, end),
                    )
                    .order_by(DocumentPage.page_number)
                )
            )
            .scalars()
            .all()
        )
    pages = [{"page": r.page_number, "text": r.text[:6000], "truncated": len(r.text) > 6000} for r in rows]
    return ToolResult(
        status="ok",
        data={"document_id": str(doc.id), "title": doc.title, "page_count": doc.page_count, "pages": pages},
        summary=f"{doc.title} pages {args.page_start}-{end}",
    )


async def get_document_outline(ctx: ToolContext, args: GetDocumentOutlineInput) -> ToolResult:
    async with get_sessionmaker()() as db:
        doc = (
            await db.execute(
                select(Document).where(
                    Document.id == args.document_id,
                    _visible(ctx.session_id, ctx.settings.auth_mode != "off"),
                )
            )
        ).scalar_one_or_none()
        if doc is None:
            return _error("DOCUMENT_NOT_FOUND", "No such document.")
        rows = (
            (
                await db.execute(
                    select(DocumentPage)
                    .where(DocumentPage.document_id == doc.id)
                    .order_by(DocumentPage.page_number)
                )
            )
            .scalars()
            .all()
        )
    headings = [
        {"text": line.strip(), "page": r.page_number, "level": line.count(".") + 1}
        for r in rows
        for line in r.text.splitlines()
        if _HEADING.match(line.strip())
    ]
    if not headings:
        return ToolResult(
            status="empty", data={"document_id": str(doc.id), "headings": []}, summary="No headings found."
        )
    return ToolResult(
        status="ok",
        data={"document_id": str(doc.id), "headings": headings[:60]},
        summary=f"{len(headings)} headings.",
    )


_TOOLS: dict[str, tuple[type[Any], Callable[[ToolContext, Any], Awaitable[ToolResult]]]] = {
    "list_documents": (ListDocumentsInput, list_documents),
    "search_documents": (SearchDocumentsInput, search_documents),
    "read_document_pages": (ReadDocumentPagesInput, read_document_pages),
    "get_document_outline": (GetDocumentOutlineInput, get_document_outline),
}


async def run_tool(
    ctx: ToolContext, name: str, raw_args: dict[str, Any], max_seconds: float | None = None
) -> ToolResult:
    """Validate, apply any injected fault, run under the tool timeout (capped by the turn's remaining time),
    and never raise."""
    if name not in _TOOLS:
        return _error("INVALID_ARGUMENT", f"Unknown tool {name}.")
    model, fn = _TOOLS[name]
    try:
        args = model.model_validate(raw_args)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(map(str, first["loc"]))
        hint = (
            " Use the document_id values (UUIDs) returned by list_documents or search_documents, "
            "never evidence IDs like E1, or leave the filter out."
            if "document_id" in where
            else " Fix the argument and call again."
        )
        return _error("INVALID_ARGUMENT", f"{where}: {first['msg']}.{hint}")
    fault = ctx.faults.take(name)

    async def attempt() -> ToolResult:
        if fault == "timeout":
            await asyncio.sleep(ctx.settings.agent_tool_timeout_s + 1)  # cancelled by wait_for below
        if fault == "error":
            return _error("DEPENDENCY_UNAVAILABLE", "Injected failure.", retryable=True)
        return await fn(ctx, args)

    limit = (
        ctx.settings.agent_tool_timeout_s
        if max_seconds is None
        else min(ctx.settings.agent_tool_timeout_s, max_seconds)
    )
    try:
        return await asyncio.wait_for(attempt(), timeout=limit)
    except TimeoutError:
        return _error("TIMEOUT", f"{name} timed out.", retryable=True)
    except Exception:
        return _error("DEPENDENCY_UNAVAILABLE", f"{name} failed.", retryable=True)
