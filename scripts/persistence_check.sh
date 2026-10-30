#!/bin/sh
set -eu

COMPOSE="${COMPOSE:-docker compose}"
BASE_URL="${POLICYPILOT_BASE_URL:-http://localhost:8080/api/v1}"
PASSCODE="${POLICYPILOT_DEMO_PASSCODE:-}"
jar="$(mktemp)"
trap 'rm -f "$jar"' EXIT
# The session cookie owns the session, so every request shares one cookie jar.
header_args="-b $jar -c $jar"
[ -n "$PASSCODE" ] && header_args="$header_args -H X-Demo-Passcode:$PASSCODE"

# shellcheck disable=SC2086
before_documents="$(curl -fsS $header_args "$BASE_URL/documents" | jq '.items | length')"
# shellcheck disable=SC2086
session_id="$(curl -fsS $header_args -X POST "$BASE_URL/sessions" | jq -er '.session_id')"

$COMPOSE restart postgres redis backend frontend >/dev/null
sleep 5

i=0
until curl -fsS $header_args "$BASE_URL/health/ready" | jq -e '.status == "ok" or .status == "degraded"' >/dev/null; do
  i=$((i + 1))
  [ "$i" -lt 60 ] || { echo "Stack did not recover after restart" >&2; exit 1; }
  sleep 2
done

# shellcheck disable=SC2086
curl -fsS $header_args "$BASE_URL/sessions/$session_id" | jq -e --arg id "$session_id" '.id == $id' >/dev/null
# shellcheck disable=SC2086
after_documents="$(curl -fsS $header_args "$BASE_URL/documents" | jq '.items | length')"
[ "$before_documents" = "$after_documents" ] || { echo "Document count changed: $before_documents -> $after_documents" >&2; exit 1; }
echo "Persistence check passed: $after_documents documents and session $session_id survived restart."
