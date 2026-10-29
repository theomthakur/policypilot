#!/bin/sh
set -eu

BASE_URL="${POLICYPILOT_BASE_URL:-http://localhost:8080/api/v1}"
PASSCODE="${POLICYPILOT_DEMO_PASSCODE:-}"
TIMEOUT_SECONDS="${SEED_TIMEOUT_SECONDS:-180}"

command -v jq >/dev/null 2>&1 || { echo "jq is required" >&2; exit 2; }

api_get() {
  if [ -n "$PASSCODE" ]; then curl -fsS -H "X-Demo-Passcode: $PASSCODE" "$BASE_URL$1"; else curl -fsS "$BASE_URL$1"; fi
}

for pdf in corpus/pdfs/*.pdf; do
  echo "Uploading $pdf"
  if [ -n "$PASSCODE" ]; then
    response="$(curl -fsS -H "X-Demo-Passcode: $PASSCODE" -F "file=@$pdf;type=application/pdf" "$BASE_URL/documents")"
  else
    response="$(curl -fsS -F "file=@$pdf;type=application/pdf" "$BASE_URL/documents")"
  fi
  run_id="$(printf '%s' "$response" | jq -er '.ingestion_run.id')"
  started="$(date +%s)"
  while :; do
    run="$(api_get "/ingestion/$run_id")"
    status="$(printf '%s' "$run" | jq -r '.status')"
    [ "$status" = "succeeded" ] && break
    [ "$status" = "failed" ] && { printf '%s\n' "$run" | jq .; exit 1; }
    [ "$(( $(date +%s) - started ))" -lt "$TIMEOUT_SECONDS" ] || { echo "Timed out waiting for $pdf" >&2; exit 1; }
    sleep 1
  done
done

count="$(api_get /documents | jq '.items | length')"
[ "$count" -ge 10 ] || { echo "Expected at least 10 indexed documents; found $count" >&2; exit 1; }
echo "Corpus ready: $count documents indexed."
