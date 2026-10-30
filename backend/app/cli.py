"""Operational commands used by deployment Jobs and init containers.

python -m app.cli wait-schema   block until the database schema is at the latest migration
python -m app.cli seed          load the bundled corpus (idempotent; one instance at a time)
"""

import asyncio
import sys
import time
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.config import get_settings
from app.db.session import get_engine


def _head() -> str:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "migrations"))
    head = ScriptDirectory.from_config(config).get_current_head()
    assert head is not None
    return head


async def wait_schema(timeout_s: float = 300.0) -> int:
    head, deadline = _head(), time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            async with get_engine().connect() as conn:
                current = (
                    await conn.execute(text("SELECT version_num FROM alembic_version"))
                ).scalar_one_or_none()
            if current == head:
                print(f"schema at head {head}")
                return 0
        except Exception as exc:  # database or table not there yet
            print(f"waiting for the schema: {type(exc).__name__}")
        await asyncio.sleep(2.0)
    print("timed out waiting for the schema", file=sys.stderr)
    return 1


async def seed() -> int:
    from app.main import _load_all

    settings = get_settings()
    loaded = await _load_all(Path(settings.corpus_dir), settings.reference_dir)
    print(f"seeded {loaded} document(s)")
    return 0


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    commands = {"wait-schema": wait_schema, "seed": seed}
    if command not in commands:
        print(__doc__, file=sys.stderr)
        return 2
    return asyncio.run(commands[command]())


if __name__ == "__main__":
    raise SystemExit(main())
