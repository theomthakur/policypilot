#!/bin/sh
set -eu

# Render assigns the actual hostname, including any uniqueness suffix.
if [ -z "${PUBLIC_ORIGIN:-}" ] && [ -n "${RENDER_EXTERNAL_URL:-}" ]; then
    export PUBLIC_ORIGIN="$RENDER_EXTERNAL_URL"
fi

if [ "${RUN_MIGRATIONS_ON_START:-true}" = "true" ]; then
    alembic upgrade head
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers
