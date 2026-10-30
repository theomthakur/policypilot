#!/usr/bin/env bash
# Failure drills against a running kind deployment. Each drill breaks something, waits for recovery and checks
# the result. Prints one line per drill; exits non-zero if a drill fails. Evidence of a full run lives in
# docs/deployment-evidence/.
set -euo pipefail
cd "$(dirname "$0")/.."
BASE="${BASE:-http://localhost:8088}"
NS=policypilot
K="kubectl -n $NS"
t0() { date +%s; }
ok() { printf 'PASS %-52s %ss\n' "$1" "$(( $(date +%s) - $2 ))"; }
fail() { printf 'FAIL %s\n' "$1"; exit 1; }
ready_api() { for _ in $(seq 1 90); do curl -fsS "$BASE/api/v1/health/ready" 2>/dev/null | grep -q '"status":"ok"' && return 0; sleep 2; done; return 1; }
psql() { $K exec statefulset/postgres -- psql -U policypilot -d "${2:-policypilot}" -Atc "$1"; }

s=$(t0); $K delete pod -l app.kubernetes.io/name=api --wait=false >/dev/null
sleep 3; $K rollout status deploy/api --timeout=240s >/dev/null; ready_api || fail "api did not recover"
ok "delete the API pod: a new one serves again" "$s"

s=$(t0); $K delete pod -l app.kubernetes.io/name=redis --wait=false >/dev/null
sleep 2; $K rollout status statefulset/redis --timeout=180s >/dev/null; ready_api || fail "api not ok after redis restart"
ok "delete the Redis pod: service stays up, cache returns" "$s"

before=$(psql "select count(*) from documents where status='ready'")
s=$(t0); $K delete pod -l app.kubernetes.io/name=postgres --wait=false >/dev/null
sleep 2; $K rollout status statefulset/postgres --timeout=240s >/dev/null; ready_api || fail "api not ok after postgres restart"
after=$(psql "select count(*) from documents where status='ready'")
[ "$before" = "$after" ] || fail "documents lost across a Postgres restart: $before -> $after"
ok "delete the PostgreSQL pod: $after documents survive (PVC)" "$s"

s=$(t0); good=$($K get deploy/api -o jsonpath='{.spec.template.spec.containers[0].image}')
$K set image deploy/api api=policypilot-backend:does-not-exist >/dev/null
sleep 25
code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/v1/health/ready"); [ "$code" = 200 ] || fail "traffic was lost during a bad rollout ($code)"
bad=$($K get pods -l app.kubernetes.io/name=api --no-headers | grep -cE 'ErrImagePull|ImagePullBackOff|Init:ErrImagePull|Init:ImagePullBackOff' || true)
[ "$bad" -ge 1 ] || fail "the bad pod was not rejected"
$K rollout undo deploy/api >/dev/null; $K rollout status deploy/api --timeout=240s >/dev/null; ready_api || fail "rollback failed"
[ "$($K get deploy/api -o jsonpath='{.spec.template.spec.containers[0].image}')" = "$good" ] || fail "rollback image differs"
ok "bad image: old pod kept serving, then rollback" "$s"

s=$(t0)
$K exec statefulset/postgres -- sh -c "pg_dump -U policypilot -d policypilot -Fc -f /tmp/drill.dump"
psql "drop database if exists policypilot_restore" postgres >/dev/null
psql "create database policypilot_restore" postgres >/dev/null
$K exec statefulset/postgres -- sh -c "psql -U policypilot -d policypilot_restore -qc 'create extension if not exists vector' && pg_restore -U policypilot -d policypilot_restore --no-owner /tmp/drill.dump >/dev/null 2>&1 || true"
restored=$(psql "select count(*) from documents where status='ready'" policypilot_restore)
[ "$restored" = "$before" ] || fail "restore has $restored documents, expected $before"
psql "drop database policypilot_restore" postgres >/dev/null
$K exec statefulset/postgres -- rm -f /tmp/drill.dump
ok "backup and restore into a scratch database ($restored documents)" "$s"
echo "recovery drills passed (worker-kill and duplicate-delivery drills: scripts/e2e/flow.mjs + docs/deployment-evidence)"
