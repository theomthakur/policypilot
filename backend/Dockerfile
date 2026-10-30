# syntax=docker/dockerfile:1.7

# ---- Build stage: resolve dependencies with uv ----
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ---- Model stage: download the embedding model once, in its own cached layer ----
FROM build AS models
ENV FASTEMBED_CACHE_PATH=/models
RUN /app/.venv/bin/python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/models')"

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime
RUN groupadd --system app && useradd --system --gid app --home /app app \
    && apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/models \
    HF_HUB_OFFLINE=1
COPY --from=build /app/.venv /app/.venv
COPY --from=models /models /models
COPY app ./app
COPY alembic.ini start.sh ./
COPY migrations ./migrations
# Group 0 gets the owner's rights so an arbitrary user ID (OpenShift) can still write /data.
RUN mkdir -p /data/uploads && chown -R app:app /data /models \
    && chgrp -R 0 /data /models && chmod -R g=u /data /models
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD curl -fsS http://localhost:8000/api/v1/health/ready || exit 1
CMD ["./start.sh"]
