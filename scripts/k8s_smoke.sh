#!/usr/bin/env bash
# Checks a running cluster deployment from the outside and the inside. Exits non-zero on the first failure.
set -euo pipefail
BASE="${BASE:-http://localhost:8088}"
NS=policypilot
ok() { printf 'ok   %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; exit 1; }

kubectl -n "$NS" get pods --no-headers | awk '$3!="Completed" && $2 !~ /^([0-9]+)\/\1$/ {bad=1; print} END{exit bad}' \
  && ok "every pod is ready" || fail "a pod is not ready"
[ "$(curl -fsS "$BASE/healthz")" = "ok" ] && ok "frontend answers through the ingress" || fail "frontend"
ready="$(curl -fsS "$BASE/api/v1/health/ready")"
echo "$ready" | grep -q '"status":"ok"' && ok "API ready: $ready" || fail "API not ready: $ready"
code="$(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/v1/documents")"
[ "$code" = 401 ] && ok "documents need a sign-in (401 when signed out)" || fail "documents returned $code when signed out"
location="$(curl -s -o /dev/null -w '%{redirect_url}' "$BASE/api/v1/auth/login")"
echo "$location" | grep -q 'localhost:8180/realms/policypilot' && ok "login redirects to the identity provider" || fail "login redirect: $location"
docs="$(kubectl -n "$NS" exec statefulset/postgres -- psql -U policypilot -d policypilot -Atc "select count(*) from documents where status='ready'")"
[ "$docs" = 14 ] && ok "14 documents are searchable" || fail "documents ready: $docs"
migs="$(kubectl -n "$NS" exec statefulset/postgres -- psql -U policypilot -d policypilot -Atc "select version_num from alembic_version")"
ok "schema at $migs"
echo "smoke passed"
