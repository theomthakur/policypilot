SHELL := /bin/sh
PYTHON ?= .venv/bin/python
COMPOSE ?= docker compose

.PHONY: setup corpus up down logs test eval eval-validate smoke redis-outage persistence backup

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r corpus/requirements.txt -r eval/requirements.txt

corpus:
	$(PYTHON) corpus/generate.py

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

test: eval-validate
	cd backend && uv run ruff check . && uv run mypy app && uv run pytest
	cd frontend && npm run lint && npm test && npm run build

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
