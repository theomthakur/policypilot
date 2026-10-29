#!/bin/sh
# Apply migrations, then start the API. Migrations are expand-and-contract only (docs/adr/0003),
# so running them on start is safe for rolling updates.
set -e
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
