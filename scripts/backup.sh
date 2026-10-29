#!/bin/sh
set -eu

COMPOSE="${COMPOSE:-docker compose}"
BACKUP_DIR="${BACKUP_DIR:-backups}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
output="$BACKUP_DIR/policypilot-$stamp.sql.gz"

$COMPOSE exec -T postgres pg_dump \
  --username "${POSTGRES_USER:-policypilot}" \
  --dbname "${POSTGRES_DB:-policypilot}" \
  --clean --if-exists --no-owner --no-privileges | gzip -9 > "$output"
shasum -a 256 "$output" > "$output.sha256"
echo "Database backup written to $output"
