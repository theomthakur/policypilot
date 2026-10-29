#!/bin/sh
# End-to-end check against a running stack: readiness, session, upload, one agent turn.
# Passes only if the answer states the expected fact AND cites the expected page of the expected document.
set -eu

BASE_URL="${POLICYPILOT_BASE_URL:-http://localhost:8080/api/v1}"
PASSCODE="${POLICYPILOT_DEMO_PASSCODE:-}"
PDF="${SMOKE_PDF:-corpus/pdfs/01-acceptable-use-and-guest-network.pdf}"
TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-120}"
QUESTION="${SMOKE_QUESTION:-What download and upload bandwidth limits apply to an unregistered device on NorthfieldGuest?}"
EXPECT_FACTS="${SMOKE_EXPECT_FACTS:-10 Mbps|2 Mbps}"          # every |-separated fact must appear in the answer
EXPECT_TITLE="${SMOKE_EXPECT_TITLE:-Guest Network}"           # a citation title must contain this
EXPECT_PAGE="${SMOKE_EXPECT_PAGE:-3}"                         # ...on this page

command -v jq >/dev/null 2>&1 || { echo "jq is required" >&2; exit 2; }
[ -f "$PDF" ] || { echo "Smoke PDF not found: $PDF" >&2; exit 2; }

jar="$(mktemp)"
trap 'rm -f "$jar"' EXIT
# The session cookie owns every resource created below, so one jar is used for every request.
call() { # call <curl args...>
  if [ -n "$PASSCODE" ]; then curl -fsS -b "$jar" -c "$jar" -H "X-Demo-Passcode: $PASSCODE" "$@"; else curl -fsS -b "$jar" -c "$jar" "$@"; fi
}

started="$(date +%s)"
until call "$BASE_URL/health/ready" 2>/dev/null | jq -e '.status == "ok" or .status == "degraded"' >/dev/null; do
  [ "$(( $(date +%s) - started ))" -lt "$TIMEOUT_SECONDS" ] || { echo "API did not become ready" >&2; exit 1; }
  sleep 2
done

session_id="$(call -X POST "$BASE_URL/sessions" | jq -er '.session_id')"

upload="$(call -F "file=@$PDF;type=application/pdf" "$BASE_URL/documents")"
run_id="$(printf '%s' "$upload" | jq -er '.ingestion_run.id')"
until ingestion="$(call "$BASE_URL/ingestion/$run_id")" && printf '%s' "$ingestion" | jq -e '.status == "succeeded" or .status == "failed"' >/dev/null; do
  [ "$(( $(date +%s) - started ))" -lt "$TIMEOUT_SECONDS" ] || { echo "Ingestion timed out" >&2; exit 1; }
  sleep 1
done
printf '%s' "$ingestion" | jq -e '.status == "succeeded"' >/dev/null || { echo "Ingestion failed" >&2; exit 1; }

body="$(jq -n --arg q "$QUESTION" '{content: $q, mode: "agent"}')"
turn_id="$(call -H "Content-Type: application/json" -d "$body" "$BASE_URL/sessions/$session_id/messages" | jq -er '.turn_id')"
until turn="$(call "$BASE_URL/turns/$turn_id")" && printf '%s' "$turn" | jq -e '.status == "completed" or .status == "failed"' >/dev/null; do
  [ "$(( $(date +%s) - started ))" -lt "$TIMEOUT_SECONDS" ] || { echo "Agent turn timed out" >&2; exit 1; }
  sleep 1
done

printf '%s' "$turn" | jq '{status, stop_reason, answer: .answer.summary, citations: .answer.citations, totals}'

printf '%s' "$turn" | jq -e '.status == "completed" and .stop_reason == "answered"' >/dev/null || { echo "FAIL: turn did not end 'answered'" >&2; exit 1; }
printf '%s' "$turn" | jq -e '(.answer.citations | length > 0) and ([.answer.citations[].verified] | all)' >/dev/null || { echo "FAIL: missing or unverified citation" >&2; exit 1; }
answer_text="$(printf '%s' "$turn" | jq -r '[.answer.summary] + [.answer.claims[].text] | join(" ")')"
old_ifs="$IFS"; IFS='|'
for fact in $EXPECT_FACTS; do
  case "$answer_text" in *"$fact"*) ;; *) IFS="$old_ifs"; echo "FAIL: answer does not contain '$fact'" >&2; exit 1 ;; esac
done
IFS="$old_ifs"
printf '%s' "$turn" | jq -e --arg t "$EXPECT_TITLE" --argjson p "$EXPECT_PAGE" \
  '[.answer.citations[] | select((.title | contains($t)) and .page == $p)] | length > 0' >/dev/null \
  || { echo "FAIL: no citation of a '$EXPECT_TITLE' document on page $EXPECT_PAGE" >&2; exit 1; }
echo "Smoke test passed."
