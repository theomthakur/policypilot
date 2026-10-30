#!/bin/sh
# Apply migrations, then start the API. Migrations are expand-and-contract only (docs/adr/0003).
# A deployment that runs migrations as its own Job (Kubernetes) sets RUN_MIGRATIONS_ON_START=false.
set -e
if [ "${RUN_MIGRATIONS_ON_START:-true}" = "true" ]; then
  alembic upgrade head
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
