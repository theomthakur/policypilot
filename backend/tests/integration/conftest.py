"""Integration fixtures: a migrated Postgres and a live Redis.

Run with INTEGRATION=1 and POSTGRES_HOST/POSTGRES_PORT/REDIS_URL pointing at test services.
"""

import asyncio
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

if os.getenv("INTEGRATION") != "1":
    pytest.skip("needs Postgres and Redis (set INTEGRATION=1)", allow_module_level=True)

BACKEND = Path(__file__).resolve().parents[2]
TABLES = (
    "citations, evidence, trace_events, turns, chunks, document_pages, ingestion_runs, "
    "documents, sessions, evaluation_cases, evaluation_runs, app_state"
)


@pytest.fixture(scope="session", autouse=True)
def _env_and_schema() -> None:
    os.environ.update(
        {"APP_ENV": "test", "LLM_PROVIDER": "fake", "EMBEDDING_PROVIDER": "fake", "CORPUS_AUTOLOAD": "false"}
    )
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, check=True)


def _clear_caches() -> None:
    from app.config import get_settings
    from app.db.session import get_engine, get_sessionmaker
    from app.ingest.embed import get_embedder
    from app.state.redis import get_redis

    for fn in (get_settings, get_engine, get_sessionmaker, get_embedder, get_redis):
        fn.cache_clear()


async def _truncate() -> None:
    from app.db.session import get_engine
    from app.state.redis import get_redis

    async with get_engine().begin() as conn:
        await conn.execute(text(f"TRUNCATE {TABLES} CASCADE"))
    await get_redis().flushdb()
    await get_redis().aclose()


@pytest.fixture(autouse=True)
def clean_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    _clear_caches()
    asyncio.run(_truncate())
    _clear_caches()
    yield
    _clear_caches()


@pytest.fixture
def client() -> Iterator[TestClient]:
    from app.main import create_app

    with TestClient(create_app()) as c:  # one event loop for the whole test
        yield c
    _clear_caches()


def clear_caches() -> None:
    """Call before switching event loops inside a test (e.g. asyncio.run, then a new TestClient)."""
    _clear_caches()


def new_session(client: TestClient) -> TestClient:
    assert client.post("/api/v1/sessions").status_code == 201
    return client
