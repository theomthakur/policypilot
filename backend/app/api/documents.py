"""Document upload, listing, page text and ingestion progress (contracts/openapi.yaml)."""

import asyncio
import hashlib
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import or_, select

from app import storage
from app.api.deps import Authenticated, CurrentSession, DbSession, Passcode
from app.api.errors import ApiError
from app.config import get_settings
from app.db.models import Document, DocumentPage, IngestionRun
from app.jobs import queue
from app.state import ingest_progress
from app.state.corpus import get_corpus_version

router = APIRouter(tags=["documents"], dependencies=[Authenticated])

PDF_MAGIC = b"%PDF-"


class DocumentOut(BaseModel):
    id: uuid.UUID
    title: str
    filename: str
    page_count: int
    status: Literal["queued", "processing", "ready", "failed"]
    source: Literal["corpus", "reference", "upload"]
    sha256: str
    error: str | None
    created_at: str

    @classmethod
    def of(cls, d: Document) -> "DocumentOut":
        return cls(
            id=d.id,
            title=d.title,
            filename=d.filename,
            page_count=d.page_count,
            status=d.status,
            source=d.source,
            sha256=d.sha256,
            error=d.error,
            created_at=d.created_at.isoformat(),
        )


class IngestionRunOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    stage: str
    pages_done: int
    page_count: int
    error: str | None

    @classmethod
    def of(cls, r: IngestionRun) -> "IngestionRunOut":
        return cls(
            id=r.id,
            document_id=r.document_id,
            status=r.status,
            stage=r.stage,
            pages_done=r.pages_done,
            page_count=r.page_count,
            error=r.error,
        )


def _write_file(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def _upload_result(document: Document, run: IngestionRun, duplicate: bool) -> dict[str, Any]:
    return {
        "document": DocumentOut.of(document),
        "ingestion_run": IngestionRunOut.of(run),
        "duplicate": duplicate,
    }


def visible_to(session_id: uuid.UUID | None) -> Any:
    """Shared corpus plus this session's uploads (REQ-F6, REQ-F7)."""
    if session_id is None:
        return Document.session_id.is_(None)
    return or_(Document.session_id.is_(None), Document.session_id == session_id)


async def _visible_document(db: DbSession, document_id: uuid.UUID, session_id: uuid.UUID | None) -> Document:
    doc = (
        await db.execute(select(Document).where(Document.id == document_id, visible_to(session_id)))
    ).scalar_one_or_none()
    if doc is None:
        raise ApiError(404, "NOT_FOUND", "Document not found.")
    return doc


@router.get("/documents")
async def list_documents(db: DbSession, session_id: CurrentSession) -> dict[str, Any]:
    rows = (
        (await db.execute(select(Document).where(visible_to(session_id)).order_by(Document.filename)))
        .scalars()
        .all()
    )
    return {"items": [DocumentOut.of(d) for d in rows], "corpus_version": await get_corpus_version(db)}


@router.post("/documents", status_code=201, dependencies=[Passcode])
async def upload_document(
    file: UploadFile,
    response: Response,
    db: DbSession,
    session_id: CurrentSession,
) -> dict[str, Any]:
    if session_id is None:
        raise ApiError(400, "INVALID_ARGUMENT", "Create a session (POST /sessions) before uploading.")
    settings = get_settings()
    limit = settings.upload_max_mb * 1024 * 1024
    data = await file.read(limit + 1)  # bounded read; uploads are small by design
    if len(data) > limit:
        raise ApiError(413, "TOO_LARGE", f"Files must be under {settings.upload_max_mb} MB.")
    if not data.startswith(PDF_MAGIC):
        raise ApiError(400, "UNSUPPORTED_PDF", "Only PDF files are accepted.")
    sha = hashlib.sha256(data).hexdigest()

    existing = (
        await db.execute(
            select(Document).where(
                Document.sha256 == sha,
                or_(Document.session_id.is_(None), Document.session_id == session_id),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        run = (
            await db.execute(
                select(IngestionRun)
                .where(IngestionRun.document_id == existing.id)
                .order_by(IngestionRun.created_at.desc())
                .limit(1)
            )
        ).scalar_one()
        response.status_code = 200
        return {
            "document": DocumentOut.of(existing),
            "ingestion_run": IngestionRunOut.of(run),
            "duplicate": True,
        }

    storage_name = f"{uuid.uuid4().hex}.pdf"  # never trust the user's filename as a path
    await storage.put(storage_name, data)
    target = Path(settings.upload_dir) / storage_name  # where a local-disk worker finds it
    filename = Path(file.filename or "upload.pdf").name[:300]
    document = Document(
        title=filename,
        filename=filename,
        storage_name=storage_name,
        sha256=sha,
        source="upload",
        session_id=session_id,
    )
    db.add(document)
    await db.flush()
    run = IngestionRun(document_id=document.id)
    db.add(run)
    await db.flush()
    await queue.enqueue(
        db,
        "ingest",
        {
            "document_id": str(document.id),
            "run_id": str(run.id),
            "path": str(target),
            "storage_key": storage_name,
            "storage": settings.storage_backend,
        },
        session_id,
        settings.job_max_attempts,
    )
    await db.commit()
    return {
        "document": DocumentOut.of(document),
        "ingestion_run": IngestionRunOut.of(run),
        "duplicate": False,
    }


@router.get("/documents/{document_id}")
async def get_document(document_id: uuid.UUID, db: DbSession, session_id: CurrentSession) -> DocumentOut:
    return DocumentOut.of(await _visible_document(db, document_id, session_id))


@router.get("/documents/{document_id}/file")
async def get_document_file(document_id: uuid.UUID, db: DbSession, session_id: CurrentSession) -> Response:
    """The original PDF, for the in-app viewer (inline, so a browser opens it instead of downloading)."""
    doc = await _visible_document(db, document_id, session_id)
    settings = get_settings()
    headers = {"Content-Disposition": f'inline; filename="{doc.filename}"'}
    if doc.source == "upload":
        data = await storage.read(doc.storage_name)
        if data is None:
            raise ApiError(404, "NOT_FOUND", "The original file is not available.")
        return Response(data, media_type="application/pdf", headers=headers)
    base = Path(settings.corpus_dir if doc.source == "corpus" else settings.reference_dir)
    path = base / doc.storage_name

    def usable() -> bool:  # file-system checks run off the event loop
        return path.is_file() and path.parent.resolve() == base.resolve()

    if not await asyncio.to_thread(usable):
        raise ApiError(404, "NOT_FOUND", "The original file is not available.")
    return FileResponse(
        path, media_type="application/pdf", filename=doc.filename, content_disposition_type="inline"
    )


@router.get("/documents/{document_id}/pages/{page}")
async def get_page(
    document_id: uuid.UUID, page: int, db: DbSession, session_id: CurrentSession
) -> dict[str, Any]:
    doc = await _visible_document(db, document_id, session_id)
    row = (
        await db.execute(
            select(DocumentPage).where(DocumentPage.document_id == doc.id, DocumentPage.page_number == page)
        )
    ).scalar_one_or_none()
    if row is None:
        raise ApiError(404, "NOT_FOUND", f"Page {page} not found.", {"page_count": doc.page_count})
    return {
        "document_id": doc.id,
        "title": doc.title,
        "page": page,
        "page_count": doc.page_count,
        "text": row.text,
    }


@router.get("/ingestion/{run_id}")
async def get_ingestion_run(run_id: uuid.UUID, db: DbSession, session_id: CurrentSession) -> dict[str, Any]:
    run = await db.get(IngestionRun, run_id)
    if run is None:
        raise ApiError(404, "NOT_FOUND", "Ingestion run not found.")
    await _visible_document(db, run.document_id, session_id)  # an upload's progress is private to its session
    cached = await ingest_progress.read(str(run_id))
    return cached if cached is not None else IngestionRunOut.of(run).model_dump(mode="json")
