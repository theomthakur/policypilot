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

# Delete a pod and wait for a DIFFERENT pod (new UID) to be Ready, so a still-terminating old pod cannot pass.
replace_pod() {
  local sel="$1" old; old=$($K get pod -l "$sel" -o jsonpath='{.items[0].metadata.uid}')
  $K delete pod -l "$sel" --wait=false ${2:-} >/dev/null
  for _ in $(seq 1 120); do
    new=$($K get pod -l "$sel" -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.uid}' 2>/dev/null || true)
    ready=$($K get pod -l "$sel" -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null || true)
    [ -n "$new" ] && [ "$new" != "$old" ] && [ "$ready" = "true" ] && return 0
    sleep 2
  done
  return 1
}

s=$(t0); replace_pod app.kubernetes.io/name=api || fail "api pod was not replaced"; ready_api || fail "api not ready again"
ok "delete the API pod: a new one serves again" "$s"

s=$(t0); replace_pod app.kubernetes.io/name=redis || fail "redis pod was not replaced"; ready_api || fail "api not ok after redis restart"
ok "delete the Redis pod: a new one serves, API stays ready" "$s"

before=$(psql "select count(*) from documents where status='ready'")
s=$(t0); replace_pod app.kubernetes.io/name=postgres || fail "postgres pod was not replaced"; ready_api || fail "api not ok after postgres restart"
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

# The worker is killed while a real question is being answered; the job lease runs out, the next worker takes it.
if [ -f .k8s-demo-credentials ] && [ -d scripts/e2e/node_modules ]; then
  s=$(t0)
  ( cd scripts/e2e && node flow.mjs --base "$BASE" --user alice --password-file ../../.k8s-demo-credentials \
      --ask "What is the minimum length of a service account password?" > /tmp/worker-kill-flow.txt 2>&1; echo $? > /tmp/worker-kill-rc ) &
  flow=$!
  # Wait until a turn job is actually running, then kill the worker that holds it.
  for _ in $(seq 1 60); do
    [ "$(psql "select count(*) from jobs where kind='turn' and status='running'")" -ge 1 ] && break; sleep 1
  done
  [ "$(psql "select count(*) from jobs where kind='turn' and status='running'")" -ge 1 ] || fail "no turn job was running"
  jid=$(psql "select id from jobs where kind='turn' and status='running' order by created_at desc limit 1")
  # A real crash: SIGKILL the worker process from the node, so there is no graceful drain.
  before_restarts=$($K get pod -l app.kubernetes.io/name=worker -o jsonpath='{.items[0].status.containerStatuses[0].restartCount}')
  docker exec "${CLUSTER:-policypilot}-control-plane" pkill -9 -f "app.jobs.worker" || fail "could not kill the worker process"
  for _ in $(seq 1 60); do
    r=$($K get pod -l app.kubernetes.io/name=worker -o jsonpath='{.items[0].status.containerStatuses[0].restartCount}')
    [ "$r" -gt "$before_restarts" ] && break; sleep 1
  done
  wait $flow; [ "$(cat /tmp/worker-kill-rc)" = 0 ] || { cat /tmp/worker-kill-flow.txt; fail "the question was lost when the worker died"; }
  row=$(psql "select status||' attempts='||attempts||' fence='||fence from jobs where id='$jid'")
  resumed=$(psql "select count(*) from trace_events where type='turn_resumed'")
  case "$row" in "succeeded attempts=2"*) ;; *) fail "job ended as '$row', expected one retry";; esac
  [ "$resumed" -ge 1 ] || fail "no turn_resumed marker in the trace"
  echo "job $row; trace shows $resumed resumed marker(s)"
  grep -E "answer:" /tmp/worker-kill-flow.txt | cut -c1-160
  ok "crash the worker mid-question: lease expires, a new worker finishes it" "$s"
else
  echo "SKIP worker-kill drill (needs .k8s-demo-credentials and scripts/e2e/node_modules)"
fi
echo "recovery drills passed"
