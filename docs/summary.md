# Summary: what was built, what is unfinished, what would come next

## What was built

PolicyPilot is a full-stack agentic RAG application over 14 PDFs: ten synthetic university IT policies (85 pages; the generator and a manifest are in `corpus/`) and four real public NIST documents (146 pages) as a reference library. A user uploads PDFs or asks questions in a browser. A single tool-using agent plans, searches, searches again with different words, reads whole pages, asks a clarifying question or answers, and every citation is checked against the actual page text before it is shown.

- **Stack:** React and TypeScript behind nginx, FastAPI, PostgreSQL with pgvector, Redis, an OpenAI-compatible model client (OpenRouter), all started by Docker Compose. CI configuration is in `.github/workflows/ci.yml`.
- **Retrieval:** page-bounded 200-token chunks, vector plus full-text search fused with reciprocal rank fusion. These settings were chosen by a benchmark on the evaluation cases' expected pages (`eval/retrieval_bench.py`, ADR 0005); a reranker, a larger embedding model and a heading prefix were tested and not adopted.
- **Agent:** a hand-written bounded state machine with four read-only tools, step, tool, time and token limits, one retry, duplicate-call blocking, partial answers on limits, and untrusted treatment of retrieved text. Greetings, thanks and questions about the assistant get a direct reply, and a question nothing in the library is about is answered in code after one search.
- **Trust:** a claim is shown only if its quote is literal text on the cited page (provenance, location, then the exact span stored as the citation).
- **Operations:** passcode, rate limit, daily budget cap, per-session isolation (a session can never read another's turns or uploads), Redis-down fallback to PostgreSQL, readiness reporting, structured logs.
- **Evaluation:** an 11-case suite run against the live API for the agent and a retrieve-once baseline; raw results are committed (`eval/results/run-2026-10-29-gpt-4o-mini-r10/`).
- **Interface:** workspace with documents, conversation and a readable execution trace; a developer mode with metrics; light and dark themes; an architecture page and a plain-language presentation.

## Results in one paragraph

On the reference run (the final 14-document library) the agent passed 6 of 11 cases and the single-pass baseline 5 of the 9 cases it applies to, on deterministic checks; the agent's average correctness is higher in both runs on this library (0.84 to 0.87 against 0.65 to 0.68), but the number of cases passed is within noise (6 of 11 both times against 4 and then 5 of 9). Citation support is complete for both because unsupported citations are never shown. The agent uses about eleven times the tokens and takes three times as long, and on direct lookups the baseline is as good and far cheaper. Runs vary by about one case. Details, the run history and the failure analysis are in `docs/evaluation.md`. The prompts were tuned against the same 11 cases, so this is a development measurement, not a held-out test.

## Unfinished

- **Five agent cases still fail** in the reference run: recognising that a newer policy replaced an older one (CASE-6), asking a clarifying question instead of answering for every variant (CASE-4), bridging everyday wording to a policy's own terms (CASE-9), wording a missing-evidence answer the way the strict check expects (CASE-5), and a follow-up that ran out of searches (CASE-11).
- **Manual citation review** (opening each cited page and judging whether it supports the claim) has not been done; the log in `docs/evaluation.md` is empty.
- **No public deployment, recorded demo or update and rollback drill** yet. The local drills (smoke test, restart persistence, Redis outage) pass and their output is saved under `docs/deployment-evidence/`.
- **CI has been configured but not yet run on GitHub**, and the work is still on the `integration/full-stack` branch, not `main`.
- No held-out evaluation set, no load testing, and the weak-evidence flag is only a hint (similarity scores cannot separate answerable from unanswerable questions here).

## With more time

1. Merge through pull requests, run CI, tag a release, publish images, deploy behind HTTPS with a capped key, and record the demo from the deployed release.
2. Write a held-out set of new questions, do the manual citation review, and re-run both systems.
3. Give the agent a structured way to flag "the answer depends on who is asking" (a plan field the code acts on) and a supersession check that compares document dates, then measure both against CASE-4 and CASE-6.
4. Query expansion from the documents' own vocabulary for the weak-wording case, then re-benchmark.
5. Move ingestion to queue workers and uploads to object storage; add SSO in place of the demo passcode; add tracing and cost dashboards.
