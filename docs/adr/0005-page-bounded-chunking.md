# 0005. Page-bounded chunking

**Status:** Accepted, 2026-10-29

## Context
Answers must cite document and page, and the evaluation checks cited pages against the supporting passages.

## Decision
Chunk each page independently: about 200 tokens with a 30-token overlap, never crossing a page boundary. Each chunk stores exactly one page number and its section heading as metadata.

## Alternatives considered
- **Cross-page chunks with page ranges:** keeps sentences that span a page break together, but citations become ambiguous.
- **Larger chunks (350 to 800 tokens, or whole pages):** more context per hit, looser citations. Measured: see below.

## Consequences
- Every citation is an exact (document, page).
- A sentence split across a page break can land in two chunks; `read_document_pages` lets the agent read adjacent pages when needed.

## Measured on the corpus (29 Oct 2026)

`eval/retrieval_bench.py` scores retrieval against the expected source pages in `eval/cases.yaml` (10 answerable cases, 15 source pages; one page of difference is noise). Averages over the hybrid variants, recall of the expected pages in the top 3 and top 5 distinct pages:

| Chunking | Recall@3 | Recall@5 | MRR |
|---|---|---|---|
| 200 / 30 (chosen) | 0.825 | 0.896 | 0.856 |
| 350 / 50 (previous) | 0.750 | 0.808 | 0.852 |
| 500 / 75 | 0.817 | 0.867 | 0.803 |
| whole page | 0.692 | 0.746 | 0.741 |

Also measured and not adopted: prefixing each chunk with the document title and section heading (no consistent gain), `bge-base-en-v1.5` instead of `bge-small` (no gain, three times the index time and a 768-dimension schema), and cross-encoder reranking with MS MARCO MiniLM models (lower recall than hybrid alone on this corpus). Adopted: the BGE query instruction on queries only (small gain, no cost). Raw numbers: `eval/results/retrieval-bench-2026-10-29.json`.

Similarity scores cannot reliably tell answerable from unanswerable questions here: the lowest cosine for an answerable question (0.728) is below the highest for an unanswerable one (0.717 to 0.752 depending on model). The `weak` flag is therefore a hint, and the agent judges sufficiency from the content it reads.

Real pipeline (Postgres full text plus pgvector, RRF) on the same gold pages, before and after adopting 200/30 chunks and the query instruction: recall@3 0.800 to 0.867, recall@5 0.867 to 0.933, MRR 0.761 to 0.883. An existing database keeps its old chunks until the corpus is re-ingested (`docker compose down -v`, or delete and re-upload documents).
