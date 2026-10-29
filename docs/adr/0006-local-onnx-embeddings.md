# 0006. Local ONNX embeddings by default

**Status:** Accepted, 2026-10-29

## Context
Ingestion and search need embeddings. A hosted embedding API would add a second key, per-request cost and a provider dependency.

## Decision
Use `fastembed` with `BAAI/bge-small-en-v1.5` (384 dimensions) running on ONNX Runtime inside the backend container. The model is downloaded at image build time so containers start offline. A configuration switch (`EMBEDDING_PROVIDER=openai`) allows a hosted model instead.

## Alternatives considered
- **Hosted `text-embedding-3-small`:** strong quality, smaller image, but adds cost, a key and a network dependency to ingestion and every search.
- **A PyTorch sentence-transformers model:** a much larger image for similar quality at this scale.

## Consequences
- No embedding cost and deterministic evaluation runs.
- The image grows by roughly 100 to 200 MB for ONNX Runtime and the model.
- Switching providers requires re-embedding the corpus (the vector dimension must match).
