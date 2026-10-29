"""Database readiness: connectivity plus "migrations are at head"."""

from pathlib import Path
from typing import Literal

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_engine

_ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _head_revision() -> str | None:
    config = Config(str(_ALEMBIC_INI))
    config.set_main_option("script_location", str(_ALEMBIC_INI.parent / "migrations"))
    return ScriptDirectory.from_config(config).get_current_head()


async def database_status() -> tuple[Literal["ok", "down"], Literal["ok", "pending", "down"]]:
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
            row = await conn.execute(text("SELECT version_num FROM alembic_version"))
            current = row.scalar_one_or_none()
    except SQLAlchemyError:
        return "down", "down"
    return "ok", ("ok" if current is not None and current == _head_revision() else "pending")
