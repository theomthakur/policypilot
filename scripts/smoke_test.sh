#!/bin/sh
set -eu

BASE_URL="${POLICYPILOT_BASE_URL:-http://localhost:8080/api/v1}"
PASSCODE="${POLICYPILOT_DEMO_PASSCODE:-}"
PDF="${SMOKE_PDF:-corpus/pdfs/01-acceptable-use-and-guest-network.pdf}"
TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-120}"

headers=""
if [ -n "$PASSCODE" ]; then
  headers="X-Demo-Passcode: $PASSCODE"
fi

api_get() {
  if [ -n "$headers" ]; then curl -fsS -H "$headers" "$BASE_URL$1"; else curl -fsS "$BASE_URL$1"; fi
}
api_post() {
  path="$1"
  body="$2"
  if [ -n "$headers" ]; then curl -fsS -H "$headers" -H "Content-Type: application/json" -d "$body" "$BASE_URL$path"; else curl -fsS -H "Content-Type: application/json" -d "$body" "$BASE_URL$path"; fi
}

command -v jq >/dev/null 2>&1 || { echo "jq is required" >&2; exit 2; }
[ -f "$PDF" ] || { echo "Smoke PDF not found: $PDF" >&2; exit 2; }

started="$(date +%s)"
until api_get /health/ready | jq -e '.status == "ok" or .status == "degraded"' >/dev/null; do
  [ "$(( $(date +%s) - started ))" -lt "$TIMEOUT_SECONDS" ] || { echo "API did not become ready" >&2; exit 1; }
  sleep 2
done

if [ -n "$headers" ]; then
  upload="$(curl -fsS -H "$headers" -F "file=@$PDF;type=application/pdf" "$BASE_URL/documents")"
else
  upload="$(curl -fsS -F "file=@$PDF;type=application/pdf" "$BASE_URL/documents")"
fi
run_id="$(printf '%s' "$upload" | jq -er '.ingestion_run.id')"

until ingestion="$(api_get "/ingestion/$run_id")" && printf '%s' "$ingestion" | jq -e '.status == "succeeded" or .status == "failed"' >/dev/null; do
  [ "$(( $(date +%s) - started ))" -lt "$TIMEOUT_SECONDS" ] || { echo "Ingestion timed out" >&2; exit 1; }
  sleep 1
done
printf '%s' "$ingestion" | jq -e '.status == "succeeded"' >/dev/null

session_id="$(api_post /sessions '{}' | jq -er '.session_id')"
question='{"content":"What limits apply to unregistered NorthfieldGuest devices?","mode":"agent"}'
turn_id="$(api_post "/sessions/$session_id/messages" "$question" | jq -er '.turn_id')"

until turn="$(api_get "/turns/$turn_id")" && printf '%s' "$turn" | jq -e '.status == "completed" or .status == "failed"' >/dev/null; do
  [ "$(( $(date +%s) - started ))" -lt "$TIMEOUT_SECONDS" ] || { echo "Agent turn timed out" >&2; exit 1; }
  sleep 1
done

printf '%s' "$turn" | jq -e '.status == "completed" and (.answer.citations | length > 0) and ([.answer.citations[].verified] | all)' >/dev/null
printf '%s' "$turn" | jq '{status, stop_reason, answer: .answer.summary, citations: .answer.citations, totals}'
echo "Smoke test passed."
