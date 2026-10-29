#!/bin/sh
set -eu

[ "$#" -eq 1 ] || { echo "Usage: CONFIRM_RESTORE=policypilot ./scripts/restore.sh backups/file.sql.gz" >&2; exit 2; }
[ "${CONFIRM_RESTORE:-}" = "policypilot" ] || { echo "Refusing restore. Set CONFIRM_RESTORE=policypilot after verifying the target and backup." >&2; exit 2; }
backup="$1"
[ -f "$backup" ] || { echo "Backup not found: $backup" >&2; exit 2; }
[ -f "$backup.sha256" ] && shasum -a 256 -c "$backup.sha256"

COMPOSE="${COMPOSE:-docker compose}"
gzip -dc "$backup" | $COMPOSE exec -T postgres psql \
  --set ON_ERROR_STOP=on \
  --username "${POSTGRES_USER:-policypilot}" \
  --dbname "${POSTGRES_DB:-policypilot}"
echo "Restore completed from $backup"
