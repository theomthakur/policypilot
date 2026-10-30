"""FastAPI application entry point."""

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response

from app.api import config, documents, health, sessions, turns
from app.api.errors import install_error_handlers
from app.config import get_settings
from app.logging import configure_logging, request_id_var

API_PREFIX = "/api/v1"

logger = logging.getLogger("policypilot")


async def _load_all(corpus_dir: Path, reference_dir: str) -> int:
    from app.ingest.pipeline import ensure_corpus_loaded

    loaded = await ensure_corpus_loaded(corpus_dir)
    if reference_dir:
        loaded += await ensure_corpus_loaded(Path(reference_dir), source="reference")
    return loaded


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    background: asyncio.Task[int] | None = None
    if settings.corpus_autoload:
        background = asyncio.create_task(_load_all(Path(settings.corpus_dir), settings.reference_dir))
    yield
    if background is not None and not background.done():
        background.cancel()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="PolicyPilot API",
        version=settings.app_version,
        lifespan=lifespan,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["x-request-id"] = request_id
        logger.info(
            "request",
            extra={
                "fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000),
                }
            },
        )
        return response

    install_error_handlers(app)
    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(sessions.router, prefix=API_PREFIX)
    app.include_router(documents.router, prefix=API_PREFIX)
    app.include_router(turns.router, prefix=API_PREFIX)
    app.include_router(config.router, prefix=API_PREFIX)
    return app


app = create_app()
