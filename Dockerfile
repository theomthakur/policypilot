# syntax=docker/dockerfile:1.7
# Single-origin deployment: React assets and FastAPI share one web service.
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS dependencies
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM dependencies AS models
ENV FASTEMBED_CACHE_PATH=/models TIKTOKEN_CACHE_DIR=/tokenizer
RUN /app/.venv/bin/python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/models')"
RUN /app/.venv/bin/python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

FROM python:3.12-slim AS runtime
RUN groupadd --system app && useradd --system --gid app --home /app app
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/models \
    TIKTOKEN_CACHE_DIR=/tokenizer \
    HF_HUB_OFFLINE=1 \
    FRONTEND_DIST_DIR=/app/frontend \
    CORPUS_DIR=/app/corpus/pdfs \
    REFERENCE_DIR=/app/corpus/reference \
    UPLOAD_DIR=/data/uploads
COPY --from=dependencies /app/.venv /app/.venv
COPY --from=models /models /models
COPY --from=models /tokenizer /tokenizer
COPY --from=frontend /frontend/dist /app/frontend
COPY backend/app ./app
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
COPY corpus/pdfs ./corpus/pdfs
COPY corpus/reference ./corpus/reference
COPY deploy/render/start.sh ./render-start.sh
RUN mkdir -p /data/uploads && chown -R app:app /data /models /tokenizer \
    && chmod 755 /app/render-start.sh
USER app
EXPOSE 8000
CMD ["./render-start.sh"]
