#!/bin/sh
set -eu

[ "$#" -eq 1 ] || { echo "Usage: ./deploy/release.sh <immutable-image-tag>" >&2; exit 2; }
export IMAGE_TAG="$1"
: "${DOMAIN:?Set DOMAIN in the environment or .env}"

COMPOSE="docker compose -f docker-compose.yml -f compose.prod.yaml"
./scripts/backup.sh
$COMPOSE pull
# WS1 supplies the migration command before deployment. Fail rather than silently deploying an unmigrated schema.
$COMPOSE run --rm backend alembic upgrade head
$COMPOSE up -d --remove-orphans
$COMPOSE ps
POLICYPILOT_BASE_URL="https://$DOMAIN/api/v1" ./scripts/smoke_test.sh
