SHELL := /bin/sh
PYTHON ?= .venv/bin/python
COMPOSE ?= docker compose

.PHONY: setup preflight corpus up down logs test test-unit verify eval eval-validate smoke redis-outage persistence backup

# Everything `make test` needs: the evaluation environment, the backend (uv) and the frontend (npm ci).
setup: preflight
	python3 -m venv .venv
	.venv/bin/pip install -r corpus/requirements.txt -r eval/requirements.txt
	cd backend && uv sync --frozen --dev
	cd frontend && npm ci

# Fails early, with a clear message, when a required tool is missing or too old.
preflight:
	@python3 -c "import sys; assert sys.version_info >= (3, 12), 'Python 3.12 or newer is required'" || exit 1
	@command -v uv >/dev/null || { echo 'uv is required: https://docs.astral.sh/uv/'; exit 1; }
	@node -e "const [a,b]=process.versions.node.split('.').map(Number); if (a<22||(a===22&&b<12)) { console.error('Node 22.12 or newer is required, found '+process.versions.node); process.exit(1) }"
	@command -v docker >/dev/null || { echo 'Docker is required'; exit 1; }
	@echo 'Preflight passed.'

corpus:
	$(PYTHON) corpus/generate.py

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

test: preflight eval-validate
	cd backend && uv run ruff check . && uv run mypy app && uv run pytest
	cd frontend && npm run lint && npm test && npm run build

# Lint, types, unit tests and the frontend, without PostgreSQL or Redis (integration tests are skipped).
test-unit: preflight
	cd backend && uv run ruff check . && uv run mypy app && uv run pytest
	cd frontend && npm run lint && npm test && npm run build

# What a reviewer should run: clone the commit and run everything CI runs, with real PostgreSQL and Redis.
verify:
	./scripts/verify_clean_checkout.sh

eval:
	$(PYTHON) eval/run.py

eval-validate:
	$(PYTHON) eval/run.py --validate-only

smoke:
	./scripts/smoke_test.sh

redis-outage:
	./scripts/redis_outage.sh

persistence:
	./scripts/persistence_check.sh

backup:
	./scripts/backup.sh
