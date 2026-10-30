#!/usr/bin/env bash
# Prove the committed repository (not your working tree) builds and passes: clone the given ref into a temporary
# directory and run lint, types, every backend test (integration included, none skipped), the contract check, the
# frontend lint/tests/build in a Node 22 container, dataset validation and manifest rendering.
#   scripts/verify_clean_checkout.sh [git-ref]        needs PostgreSQL+pgvector and Redis for the integration tests:
#   POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=55432 POSTGRES_PASSWORD=... REDIS_URL=redis://127.0.0.1:56379/0 ...
set -euo pipefail
REF="${1:-HEAD}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
git -C "$ROOT" clone -q "$ROOT" "$WORK/repo"
git -C "$WORK/repo" checkout -q "$REF"
cd "$WORK/repo"
echo "== checking out $(git rev-parse --short HEAD)"

echo "== backend: lint, types, tests"
(cd backend && uv sync --frozen --dev -q && uv run ruff check . && uv run mypy app >/dev/null && echo "lint and types ok")
(cd backend && INTEGRATION=1 APP_ENV=test LLM_PROVIDER=fake EMBEDDING_PROVIDER=fake CORPUS_AUTOLOAD=false \
  uv run pytest -q -rs 2>&1 | tee /tmp/clean-pytest.log | tail -3)
! grep -q SKIPPED /tmp/clean-pytest.log || { echo "tests were skipped"; exit 1; }
(cd backend && uv run python ../scripts/check_contract.py)

echo "== frontend (Node 22 container): lint, tests, build"
docker run --rm -v "$PWD/frontend":/app -w /app node:22-alpine sh -c "npm ci --silent && npm run lint && npm test -- --run && npm run build" 2>&1 | tail -6

echo "== evaluation datasets and manifests"
python3 -m venv "$WORK/venv" && "$WORK/venv/bin/pip" install -q -r eval/requirements.txt
"$WORK/venv/bin/python" eval/run.py --validate-only
"$WORK/venv/bin/python" eval/run.py --cases eval/heldout.yaml --validate-only
for overlay in kind openshift; do kubectl kustomize deploy/k8s/overlays/$overlay >/dev/null && echo "kustomize $overlay renders"; done
echo "clean checkout verified: $(git rev-parse HEAD)"
