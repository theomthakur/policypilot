# Scorecard against the take-home brief

Source: `Take-Home-Agentic-RAG-Brief.pdf` (NYU IT, AI Engineer, Agentic RAG). Updated 31 Oct 2026 from the integrated branch. Every item in the brief is listed in its own order. **Score** is my own honest rating out of 10 for how well the submission meets that item (10 = nothing a reviewer could fault). **Evidence** points at the file, test or saved output that backs it. **To improve** says what would raise the score.

Status: **DONE** (built and verified), **PARTIAL** (works, something named is open), **OPEN** (not done, needs the author).

## Summary

| Area | Score | Where it is weakest |
|---|---:|---|
| 2. Problem statement | 8.7 | Agent still fails some new questions |
| 3. Expected components A to J | 8.5 | The weak-result search case, and the size of the evaluation |
| 4. Eight required test cases | 8.6 | Citation spot-check still to do by the author |
| 5. Technology | 9.5 | None |
| 6. What to submit | 8.2 | Demo not recorded |
| 7. Interview preparation | 7.0 | Needs rehearsal by the author |
| 8. Optional enhancements | 8.3 | OpenShift not run on a real cluster |
| **Overall** | **8.6** | Demo recording and evaluation noise |

## 2. Problem statement

| Item | Status | Score | Evidence | To improve |
|---|---|---:|---|---|
| Full-stack agentic RAG app over about 8 to 15 text PDFs from one domain | DONE | 9 | 14 PDFs (10 synthetic Northfield IT policies, 4 NIST documents), `corpus/` | None needed |
| Users can upload documents | DONE | 9 | `POST /api/v1/documents`, ingestion tests, upload row in the sidebar | None |
| Users can ask simple and multi-part questions | DONE | 9 | CASE-1, 2, 3, 10 | None |
| Agent chooses tools and decides: retrieve more, clarify, or answer with citations | DONE | 8 | `backend/app/agent/loop.py`, traces in `eval/results/` | Clarify decision is the weakest branch and was tuned on known questions |
| Working containerized deployment | DONE | 9 | `docker-compose.yml`, smoke test, `docs/deployment-evidence/2026-10-30/` | Not deployed publicly |
| Corpus included or reproducible | DONE | 9 | `corpus/` plus manifest and generator, `docs/reproducibility.md` | None |
| Unfinished work documented | DONE | 9 | `docs/summary.md`, `docs/evaluation.md` | Keep numbers in sync before submitting |
| A single agent is enough | DONE | 10 | One agent, no multi-agent code | None |

## 3. Expected components

| Component | Status | Score | Evidence | To improve |
|---|---|---:|---|---|
| **A. Application architecture**: frontend and backend, API layer, usable UI | DONE | 9 | React/Vite UI, FastAPI, `contracts/openapi.yaml` checked in CI; one sidebar for all pages, session history, knowledge-base folders, light and dark themes | A person should click through every flow once |
| **B. RAG pipeline**: parse, chunk, index, retrieve, grounded generation, page metadata kept | DONE | 9 | `backend/app/ingest/`, `retrieval/hybrid.py`, ADR 0005 (benchmark of options) | Section names are empty on institutional chunks (known, does not affect citations) |
| **C. Adaptive orchestration**: decompose, revise after weak results, combine documents, show a result-driven change of action | DONE | 8 | CASE-2, 3, 4, 8, 11 traces; `query_revised` events (mostly for a part the first search missed) | CASE-9, the weak-result case, failed all three final runs; CASE-11 reached the call limit in one run of three |
| **D. Tool contracts**: at least three read-only tools, validation, empty-result and error handling | DONE | 9 | `list_documents`, `search_documents`, `read_document_pages`, `get_document_outline`; `contracts/tools.schema.json` | None needed |
| **E. State and observability**: per-session state, UI trace, timing, tokens | DONE | 9 | Trace events with tools, inputs, summaries, status, citations, tokens; Agent activity tab; session history | None |
| **F. Execution safety**: step limits, timeouts, bounded retries, partial answers, untrusted text, corpus-only tools, isolated sessions | DONE | 9 | CASE-7, CASE-8, limit tests, per-user ownership, CSRF guard | None needed |
| **G. Persistence and Redis**: database, real Redis use, keys, expiry, outage behavior | DONE | 8 | Postgres plus Redis (cache, hot state, budget counters), outage script and saved output | Redis key and expiry table should be one page in the runbook |
| **H. Containerization and DevOps**: Dockerfiles, Compose, health checks, volumes, secrets, CI, smoke test, persistence, outage, update and rollback | DONE | 8 | Compose, CI (ruff, mypy, pytest, builds; green on the latest finished runs), `docs/runbook.md`, kind and Calico verification | No public deploy |
| **I. Evaluation**: 8+ cases, expected sources, results and failure analysis, baseline on the same corpus and model, traces, exclusions | DONE | 7.5 | `eval/run.py`, `eval/cases.yaml` (11 cases), `docs/evaluation.md`; final run agent 29 of 33 (three runs), newer set 18 of 18, older held-out 12 of 20; baseline 15 of 27, 10 of 14, 12 of 18 | Single runs; several disclosed label corrections; held-out sets no longer blind |
| **J. Engineering quality**: practices, organization, documentation | DONE | 9 | 173 backend tests and 23 frontend tests on the integrated release, typed config, ADRs, requirements traceability | Keep the final release checks and documentation synchronized |

## 4. Required demonstration and test cases

The canonical measurements are the 31 Oct `r31-*` repeated runs at the top of [`evaluation.md`](evaluation.md). Older measurements remain as experiment history only. "Agent / baseline" below summarizes the canonical record.

| Case | Pass criterion (from the brief) | Agent / baseline | Score | To improve |
|---|---|---|---:|---|
| 1. Simple lookup | Directly supported fact with the right page | pass / pass | 10 | None |
| 2. Multi-part, multi-document A | All parts, at least two documents | pass / pass | 9 | None |
| 3. Multi-part, multi-document B | Second cross-document question, each claim cited | passed all three final runs / fails (baseline 0 of 3) | 9 | None |
| 4. Ambiguous question | Ask a targeted clarification, keep context | asks which account type and answers correctly: passed all three final runs / not applicable | 8 | Passes reliably on the measured questions; not proven on new ones |
| 5. Insufficient evidence | Say evidence is missing, no invented citation | pass / pass | 9 | None |
| 6. Conflicting sources | Cite both passages, explain, do not silently choose | passed all three final runs / fails (baseline 0 of 3) | 8 | Built on a two-passage template; documented scope terms needed |
| 7. Prompt injection | Ignore instructions in retrieved text | pass / pass | 9 | None |
| 8. Tool failure or timeout | Bounded retry or graceful recovery, report incomplete work | pass / not applicable | 9 | None |
| Citation verification | Check cited pages against supporting passages | automated quote check on every citation | 7 | A manual spot-check of about 20 citations is still to be done by the author |
| Agent against baseline, where iteration helps or costs | Report correctness, citation support, completion, calls, latency, cost | reported; the agent costs about 25 to 30 times the baseline per question | 8 | The overhead is stated openly |

Not passing in the final runs and stated openly in `docs/evaluation.md`: CASE-9 (failed 3 of 3), CASE-11 (failed 1 of 3, reached the call limit); on the older held-out set HELD-2, 7, 8 and 9 (failed both runs).

## 5. Technology

| Item | Status | Score | Evidence | To improve |
|---|---|---:|---|---|
| Redis and Docker required | DONE | 10 | Compose runs both; Redis has a functional purpose | None |
| PostgreSQL preferred | DONE | 10 | PostgreSQL 16 with pgvector and full-text index | None |
| Whole stack runs through Docker Compose | DONE | 9 | `docker compose up`, `scripts/verify_clean_checkout.sh` | Run the clean-checkout script once more on the final commit |
| AI-assisted coding allowed, but must be explainable | DONE | 9 | Design notes, ADRs, trace of decisions | Author must be able to explain every module |

## 6. What to submit

| Item | Status | Score | Evidence | To improve |
|---|---|---:|---|---|
| GitHub repository with setup instructions | DONE | 9 | github.com/theomthakur/policypilot, `README.md`, tags `v0.2.0-rc1` to `rc4` | Merge `integration/full-stack` to `main` (author) |
| Reproducibility notes: corpus, model and embedding IDs, prompts, tool schemas, env template, evaluation command, expected cost | DONE | 9 | `docs/reproducibility.md`, `.env.example`, `backend/app/agent/prompts/`, `contracts/tools.schema.json` | None |
| Architecture diagram: components, agent state, tool calls, decision points, retrieval loop, stopping conditions | DONE | 9 | The System design page (one flow from upload to answer, with where Compose, Kubernetes and OpenShift fit) and `docs/system-design.md` | `docs/system-design.md` text is longer than the page and not re-read since 29 Oct |
| Agent and baseline evaluation results and failure analysis | DONE | 8 | `docs/evaluation.md`, saved traces | Pass rate and single-run noise |
| Short recorded demo or reproducible walkthrough (multi-document question, re-retrieval, clarification, failed tool call, saved traces) | **OPEN** | 4 | Walkthrough script `docs/demo.md` is ready; no recording made | **Record the demo** (author) |
| Short summary of achievements, unfinished work, improvements | DONE | 9 | `docs/summary.md` | None |
| Deployment runbook and evidence: Dockerfiles, Compose, CI, deploy/verify/update/rollback commands, health output, end-to-end request, config and secrets, persistence, logging, scaling | DONE | 8 | `docs/runbook.md`, `docs/deployment-evidence/2026-10-30/`, `docs/kubernetes.md` | No public deployment |

## 7. Interview preparation

| Item | Status | Score | Evidence | To improve |
|---|---|---:|---|---|
| Walk through thinking, decisions and trade-offs | PARTIAL | 8 | `docs/presentation.md`, ADRs 0001 to 0011 | Rehearse a 5-minute and a 20-minute version |
| Be open to feedback | n/a | n/a | Behavior in the room | None |
| Focus on what matters most and explain what is unfinished | DONE | 8 | `docs/summary.md` lists open items | None |
| Be ready for a code walkthrough and a small change | PARTIAL | 6 | Tests make small changes safe | Practice changing a prompt, a limit and one tool live, from a clean checkout |

## 8. Optional enhancements

| Item | Status | Score | Evidence | To improve |
|---|---|---:|---|---|
| Authentication and personalization | DONE | 9 | OIDC with PKCE, per-user ownership, `docs/authentication.md`; saved session history | History list is per browser |
| Advanced retrieval | DONE | 8 | Hybrid ranking, policy-family discovery, supersession metadata, measured against alternatives | Section names missing on institutional chunks |
| Infrastructure as code, Kubernetes, OpenShift | DONE | 8 | Kustomize base, overlays, network policies, S3 storage; verified on kind with Calico; OpenShift overlay is render-only | OpenShift not run on a real cluster |

## Decisions

- **No public deployment.** The brief asks for a working Docker Compose deployment with runbook and evidence, which exists (Compose, CI, health output, smoke test, persistence and Redis-outage scripts). A public URL is not required, so it is not planned.
- **OpenShift on hold.** The overlay is written and rendered but not run on a cluster; the System design page says so.

## What is still needed, in order

**Author only**
1. Record the demo from `docs/demo.md` (the only required item still missing).
2. Spot-check about 20 citations by hand and note it in `docs/evaluation.md`.
3. Merge `integration/full-stack` to `main` and open the PR.
4. Rehearse the walkthrough and one live code change.
5. Submit by 12 PM on Sunday 1 Nov.

**Mine, still open**
1. Quick mode shows "Found nothing" in the activity panel even when it found a passage (display bug, Developer mode only).
2. A full evaluation run on the final commit, to replace the numbers in the canonical block at the top of `docs/evaluation.md` (needs model credit).
3. Run `scripts/verify_clean_checkout.sh` on the final commit and confirm CI is green on it.
4. Put the coding-agent transcripts inside the repo.
5. Restore the daily budget cap to 1.00 (temporarily 1.85) and tag the final release.

**Decision for the author**
- Whether to try a gentle "you have enough, answer now" nudge for CASE-11 (reaches the six-call limit with a correct answer).

**Known weak spots, not planned**
- CASE-9 fails and CASE-11 failed once in three runs; HELD-2, 7, 8 and 9 fail; no set is blind and the samples are small.
- A deterministic clarification layer, answer prose built only from verified claims, and a repair path for adaptive search are future work.
