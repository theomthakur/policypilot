# 0003. PostgreSQL + pgvector as the single durable store

**Status:** Accepted, 2026-10-29

## Context
We need durable storage for documents, pages, chunks, embeddings, sessions, turns, traces and evaluation runs, plus vector and keyword search. The brief prefers PostgreSQL.

## Decision
Use PostgreSQL 16 with the pgvector extension. Embeddings live in a `vector(384)` column with an HNSW cosine index; full-text search uses a generated `tsvector` column with a GIN index. Schema changes use Alembic with expand-and-contract migrations.

## Alternatives considered
- **A dedicated vector database** (Qdrant, Weaviate, Chroma): strong at large scale, but a second store to deploy, back up and keep consistent.
- **In-memory vectors:** fast for a small corpus, but not durable and not shared across API replicas.

## Consequences
- One transactional store: a document is either fully ingested or invisible to search.
- Metadata filters, vector search and keyword search run in one query engine.
- At very large scale the vector index may need partitioning or a dedicated store; noted as a scaling path.
