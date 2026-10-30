"""Ingestion pipeline: parse -> chunk -> embed -> store, in one transaction per document.

A document becomes searchable only when every page and chunk is stored, so a failure never leaves
partial chunks visible (status stays `failed` with the error recorded).
"""

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Chunk, Document, DocumentPage, IngestionRun
from app.db.session import get_sessionmaker
from app.ingest.chunk import chunk_pages
from app.ingest.embed import get_embedder
from app.ingest.parse import UnsupportedPdfError, parse_pdf
from app.state import ingest_progress
from app.state.corpus import bump_corpus_version

logger = logging.getLogger("policypilot.ingest")

PARSER_VERSION = "pymupdf-v1"
CHUNKER_VERSION = "page-bounded-sentences-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


async def _progress(db: AsyncSession, run: IngestionRun, stage: str, status: str = "running") -> None:
    run.stage, run.status = stage, status
    await db.commit()
    await ingest_progress.publish(
        str(run.id),
        {
            "id": str(run.id),
            "document_id": str(run.document_id),
            "status": run.status,
            "stage": run.stage,
            "pages_done": run.pages_done,
            "page_count": run.page_count,
            "error": run.error,
        },
    )


async def ingest_document(document_id: uuid.UUID, run_id: uuid.UUID, path: Path) -> None:
    settings = get_settings()
    async with get_sessionmaker()() as db:
        document = await db.get(Document, document_id)
        run = await db.get(IngestionRun, run_id)
        if document is None or run is None:
            return
        try:
            document.status = "processing"
            await _progress(db, run, "parsing")
            parsed = await asyncio.to_thread(parse_pdf, path, settings.upload_max_pages)
            run.page_count = document.page_count = len(parsed.pages)
            if document.source in ("corpus", "reference") or document.title == document.filename:
                document.title = _sidecar_title(path) or parsed.title

            await _progress(db, run, "chunking")
            chunks = chunk_pages(parsed.pages, settings.chunk_tokens, settings.chunk_overlap_tokens)

            await _progress(db, run, "embedding")
            vectors = await asyncio.to_thread(get_embedder().embed, [c.text for c in chunks])

            await _progress(db, run, "indexing")
            await db.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
            await db.execute(delete(Chunk).where(Chunk.document_id == document.id))
            db.add_all(
                DocumentPage(
                    document_id=document.id,
                    page_number=p.number,
                    text=p.text,
                    text_hash=hashlib.sha256(p.text.encode()).hexdigest(),
                )
                for p in parsed.pages
            )
            db.add_all(
                Chunk(
                    document_id=document.id,
                    page_number=c.page_number,
                    chunk_index=c.chunk_index,
                    section=c.section,
                    text=c.text,
                    token_count=c.token_count,
                    embedding=v,
                )
                for c, v in zip(chunks, vectors, strict=True)
            )
            document.status = "ready"
            document.error = None
            run.pages_done = run.page_count
            run.status, run.stage = "succeeded", "done"
            run.finished_at = datetime.now(UTC)
            run.versions = {
                "parser": PARSER_VERSION,
                "chunker": CHUNKER_VERSION,
                "embedding_model": settings.embedding_model,
            }
            await bump_corpus_version(db)
            await _progress(db, run, "done", "succeeded")
            fields = {"document_id": str(document.id), "chunks": len(chunks)}
            logger.info("ingested", extra={"fields": fields})
        except Exception as exc:
            await db.rollback()
            message = str(exc) if isinstance(exc, UnsupportedPdfError) else "Ingestion failed."
            document = await db.get(Document, document_id)
            run = await db.get(IngestionRun, run_id)
            if document is not None and run is not None:
                document.status, document.error = "failed", message
                run.error, run.finished_at = message, datetime.now(UTC)
                await _progress(db, run, "failed", "failed")
            logger.exception("ingestion failed", extra={"fields": {"document_id": str(document_id)}})


def _corpus_files(corpus_dir: Path) -> list[Path]:
    return sorted(corpus_dir.glob("*.pdf")) if corpus_dir.is_dir() else []


def _sidecar_title(path: Path) -> str | None:
    """Optional display title from a titles.json next to the PDFs (real documents have messy metadata)."""
    sidecar = path.parent / "titles.json"
    try:
        return str(json.loads(sidecar.read_text()).get(path.name)) if sidecar.is_file() else None
    except (OSError, ValueError):
        return None


_METADATA_KEYS = ("authority", "version", "effective_date", "doc_family", "supersedes")


def sidecar_metadata(path: Path) -> dict[str, object]:
    """Descriptive metadata for a bundled PDF from a metadata.json next to it. Uploads never have any."""
    sidecar = path.parent / "metadata.json"
    try:
        entry = json.loads(sidecar.read_text()).get(path.name) if sidecar.is_file() else None
    except (OSError, ValueError):
        return {}
    return {k: entry[k] for k in _METADATA_KEYS if k in entry} if isinstance(entry, dict) else {}


def apply_metadata(document: Document, path: Path) -> bool:
    """Set the sidecar metadata on a bundled document. Returns True when anything changed."""
    changed = False
    for key, value in sidecar_metadata(path).items():
        if getattr(document, key) != value:
            setattr(document, key, value)
            changed = True
    return changed


async def ensure_corpus_loaded(corpus_dir: Path, source: str = "corpus") -> int:
    """Ingest bundled PDFs not stored yet (matched by SHA-256). Returns how many were ingested."""
    queued = 0
    for path in await asyncio.to_thread(_corpus_files, corpus_dir):
        digest = await asyncio.to_thread(sha256_file, path)
        async with get_sessionmaker()() as db:
            existing = (
                await db.execute(
                    select(Document).where(Document.sha256 == digest, Document.session_id.is_(None))
                )
            ).scalar_one_or_none()
            if existing is not None and existing.status == "ready":
                if apply_metadata(existing, path):
                    await bump_corpus_version(db)  # cached search results carry metadata
                    await db.commit()
                continue
            if existing is None:
                existing = Document(
                    title=path.stem,
                    filename=path.name,
                    storage_name=path.name,  # corpus files live in CORPUS_DIR
                    sha256=digest,
                    source=source,
                    status="queued",
                )
                apply_metadata(existing, path)
                db.add(existing)
                await db.flush()
            run = IngestionRun(document_id=existing.id)
            db.add(run)
            await db.commit()
            document_id, run_id = existing.id, run.id
        await ingest_document(document_id, run_id, path)
        queued += 1
    return queued
