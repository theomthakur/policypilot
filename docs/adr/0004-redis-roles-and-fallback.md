# 0004. Redis roles, keys and fallback

**Status:** Accepted, 2026-10-29

## Context
The brief requires Redis with a real purpose, documented keys and expiry, and defined behavior when Redis is unavailable.

## Decision
Redis holds fast, disposable state; PostgreSQL remains the source of truth.

| Key | Purpose | Expiry |
|---|---|---|
| `session:{id}` | Hot session snapshot (recent turns, pending clarification, evidence IDs) | 24 h sliding |
| `search:{corpus_version}:{query_hash}:{filter_hash}` | Search result cache | 15 min |
| `ingest:{run_id}` | Ingestion progress for the UI | 1 h after completion |
| `ratelimit:{client}:{window}` | Per-client request limit | One window |
| `budget:{yyyy-mm-dd}` | Daily model-spend counter; new model calls fail closed past the cap | 48 h |
| `corpus:version` | Cache invalidation counter, also stored in PostgreSQL | None |

When Redis is unavailable: readiness reports `degraded`; sessions read and write PostgreSQL directly; search runs uncached; ingestion progress is read from PostgreSQL; rate limiting falls back to an in-process limiter; the budget is read from PostgreSQL usage totals.

## Alternatives considered
- **No Redis:** violates the brief.
- **Redis as the only session store:** sessions would be lost in an outage.

## Consequences
- A Redis outage degrades speed, not correctness.
- Cache entries become unreachable when the corpus version changes, so stale results are never served.
