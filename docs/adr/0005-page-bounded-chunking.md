# 0005. Page-bounded chunking

**Status:** Accepted, 2026-10-29

## Context
Answers must cite document and page, and the evaluation checks cited pages against the supporting passages.

## Decision
Chunk each page independently: about 350 tokens with a 50-token overlap, never crossing a page boundary. Each chunk stores exactly one page number and its section heading as metadata.

## Alternatives considered
- **Cross-page chunks with page ranges:** keeps sentences that span a page break together, but citations become ambiguous.
- **Larger chunks (500 to 800 tokens):** more context per hit, looser citations. Compared once in the evaluation.

## Consequences
- Every citation is an exact (document, page).
- A sentence split across a page break can land in two chunks; `read_document_pages` lets the agent read adjacent pages when needed.
