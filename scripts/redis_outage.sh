#!/bin/sh
set -eu

COMPOSE="${COMPOSE:-docker compose}"
BASE_URL="${POLICYPILOT_BASE_URL:-http://localhost:8080/api/v1}"
PASSCODE="${POLICYPILOT_DEMO_PASSCODE:-}"
header_args=""
[ -n "$PASSCODE" ] && header_args="-H X-Demo-Passcode:$PASSCODE"

restore_redis() {
  $COMPOSE start redis >/dev/null 2>&1 || true
}
trap restore_redis EXIT INT TERM

$COMPOSE stop redis
sleep 2
# shellcheck disable=SC2086
health="$(curl -fsS $header_args "$BASE_URL/health/ready")"
printf '%s' "$health" | jq -e '.status == "degraded" and .checks.redis == "down"' >/dev/null

# A session and turn must remain usable through the documented PostgreSQL/uncached fallback.
# shellcheck disable=SC2086
session_id="$(curl -fsS $header_args -X POST "$BASE_URL/sessions" | jq -er '.session_id')"
# shellcheck disable=SC2086
turn_id="$(curl -fsS $header_args -H 'Content-Type: application/json' -d '{"content":"What is the NorthfieldGuest download limit?","mode":"agent"}' "$BASE_URL/sessions/$session_id/messages" | jq -er '.turn_id')"

i=0
while [ "$i" -lt 60 ]; do
  # shellcheck disable=SC2086
  turn="$(curl -fsS $header_args "$BASE_URL/turns/$turn_id")"
  status="$(printf '%s' "$turn" | jq -r '.status')"
  [ "$status" = "completed" ] && break
  [ "$status" = "failed" ] && { printf '%s\n' "$turn"; exit 1; }
  i=$((i + 1))
  sleep 1
done
[ "${status:-}" = "completed" ] || { echo "Turn did not complete while Redis was down" >&2; exit 1; }

printf '%s\n' "$health" | jq .
echo "Redis outage fallback passed. Redis will now be restarted."
