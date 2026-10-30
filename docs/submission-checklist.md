# Submission checklist against the take-home brief

Status as of 29 Oct 2026, from the integrated branch (`integration/full-stack`). Legend: **[x] done** (built and verified by a test, a run or saved output), **[~] partial** (works, something named is open), **[ ] pending** (not done). The wording of each requirement is paraphrased from the brief.

## 1. The problem statement

- [x] Full-stack agentic RAG app over about 8 to 15 text PDFs from one domain. (10 synthetic university IT policies, 74 pages.)
- [x] Users can upload documents and ask simple or multi-part questions.
- [x] The agent chooses tools, inspects results, and decides between retrieving more, asking for clarification, or answering with document and page citations.
- [~] Asking for clarification works in the code and in tests, but the real model only asks about half the time it should (see CASE-4 below).
- [x] Working containerized deployment (Docker Compose runs all four services and passes the smoke test locally).
- [x] The corpus is included, with a reproducible generator and a manifest (`corpus/`). Documents support cross-document questions.
- [~] Unfinished work is documented (`docs/summary.md`, `docs/evaluation.md`).

## 2. Expected components (A to J)

**A. Application architecture**
- [x] Frontend and backend are separate services connected by a REST API (`contracts/openapi.yaml`, drift-checked in CI).
- [x] A clean, usable UI: documents, conversation, citation drawer, execution trace, light and dark themes, developer mode.
- [~] The UI was checked by tests, a production build and headless screenshots, not by a person clicking through every flow.

**B. RAG pipeline**
- [x] PDF parsing, chunking, indexing, retrieval and source-grounded generation, with document and page metadata kept.
- [x] Retrieval settings chosen by measurement (200-token chunks, hybrid search); the benchmark and the options that lost are in ADR 0005.

**C. Adaptive agent orchestration**
- [x] LLM-driven tool-use loop (not retrieve-then-generate): plans sub-questions, searches, reads pages, re-searches, combines documents.
- [x] Queries are revised after weak or incomplete results, and every revision is shown in the trace.
- [x] At least one result-driven change of action is demonstrated (follow-up searches in CASE-2, 3, 9, 11 traces).
- [~] The adaptive case built to show it (CASE-9) fails in the final run because of vocabulary mismatch, not because the loop is missing.

**D. Tool contracts**
- [x] Four distinct read-only tools: `list_documents`, `search_documents`, `read_document_pages`, `get_document_outline`.
- [x] Structured input and output, argument validation, empty-result handling and error handling (unit and integration tests).
- [~] Schemas are enforced by Pydantic models; `contracts/tools.schema.json` is documentation, not what validates.

**E. State and observability**
- [x] Per-session question, tool-result, evidence and clarification state (Postgres durable, Redis hot copy).
- [x] UI execution trace with tool, input, result summary, status and citations, in plain words; raw details and timings under Developer mode.
- [x] Timing and token usage are recorded for every turn (latency, prompt and completion tokens, estimated cost).
- [x] No private chain of thought is exposed; the trace holds actions and summaries only.

**F. Execution safety**
- [x] Configurable step, tool-call, time and token limits; tool timeouts; one bounded retry; a useful partial answer when a limit is hit.
- [x] Retrieved instructions are treated as untrusted (CASE-7 passes); tools only see the corpus and the session's own uploads.
- [x] Sessions are isolated: another session's cookie gets 404 on sessions, turns, event streams, uploads and ingestion progress (tests).

**G. Persistence and Redis**
- [x] PostgreSQL holds everything durable; Redis has real jobs (session state, search cache keyed by corpus version, ingest progress, rate limits, daily budget).
- [x] Keys and expiry are documented (ADR 0004); behavior when Redis is down is "degraded, still works" and is demonstrated: `docs/deployment-evidence/redis-outage.txt`.
- [x] Data survives a restart: `docs/deployment-evidence/persistence-check.txt`.

**H. Containerization and DevOps**
- [x] Dockerfiles, Compose, environment template without secrets, health checks (readiness-based), named volumes.
- [x] Smoke test passes and asserts the expected fact and cited page: `docs/deployment-evidence/smoke-test.txt`.
- [~] CI workflow exists (tests including integration, contract drift, image builds, secret scan) but has **not run on GitHub yet**; it triggers on pull requests and on `main`.
- [ ] Production images are not published; the production Compose file expects immutable images.
- [~] Update and rollback instructions are written (`docs/runbook.md`) but no update/rollback drill has been run.

**I. Evaluation**
- [x] Repeatable evaluation script with 11 cases, expected behavior and expected sources (`eval/run.py`, `eval/cases.yaml`).
- [x] Actual results and a failure analysis (`docs/evaluation.md`), compared with a single-pass retrieve-once baseline on the same corpus and model, with traces committed and exclusions explained (CASE-4 and CASE-8 are not applicable to the baseline).
- [x] The write-up says where iteration helps and where it only adds cost; the agent does not win every case.
- [ ] Manual citation check (opening each cited page and judging the claim) is not done; the log in `docs/evaluation.md` is empty. Automatic check: every shown citation is literal text on its page (14 of 14).

**J. Engineering quality**
- [x] Clear module layout, ADRs, 76 backend tests and 15 frontend tests, ruff and strict mypy, ESLint, TypeScript, Prettier.
- [~] Tests pass locally; they have not yet run in GitHub Actions.

## 3. Required test cases (final run r8, agent vs baseline)

Each case records expected behavior, actual result, citations, pass or fail, tool calls, latency, tokens and a failure note in `eval/results/run-2026-10-29-gpt-4o-mini-r8/`.

- [x] 1 Simple lookup: pass, pass
- [x] 2 Multi-document A: pass, pass
- [x] 3 Multi-document B: pass, pass (flipped to fail in one earlier run; treat as unstable)
- [ ] 4 Ambiguous question: **fail** (answers for every account type instead of asking); baseline not applicable
- [ ] 5 Insufficient evidence: **fail** for both on the strict wording check; the agent asked a question instead of reporting missing evidence, the baseline's answer was right in different words
- [ ] 6 Conflicting sources: **fail** for both (finds the 2023 policy, never the 2025 one that replaces it)
- [x] 7 Prompt injection: pass, pass
- [x] 8 Tool failure or timeout: pass; baseline not applicable
- [ ] 9 Adaptive re-retrieval (extra): **fail** for both (everyday wording does not match the policy's terms)
- [x] 10 One document, many parts (extra): pass, pass
- [x] 11 Follow-up question (extra): pass for the agent, fail for the baseline (the intended weakness)

Result: agent 7 of 11, baseline 5 of 9 (agent 6 of the same 9). Agent citation support 14 of 14, baseline 11 of 11. The agent uses about eight times the tokens. Prompts were tuned on these same cases and runs vary by about one case, so treat it as a development measurement.

## 4. Technology

- [x] Redis and Docker are used and required; PostgreSQL; FastAPI; React and TypeScript; the whole stack runs through Docker Compose.
- [x] AI-assisted coding is allowed if you can explain the code. That part is yours: see "Before the interview" below.

## 5. What to submit

- [~] GitHub repository with implementation and setup instructions: code and README are on `integration/full-stack`; `main` still holds only the first commit, so open pull requests and merge.
- [x] Reproducibility notes: corpus source, model and embedding IDs, prompts, tool schemas, environment template, evaluation command, expected cost (`docs/reproducibility.md`).
- [x] System design and architecture diagram with components, agent states, tool calls, decision points, retrieval loop and stopping conditions (`docs/architecture.md`, `docs/system-design.md`, the in-app System design page).
- [x] Agent and baseline evaluation results and failure analysis (`docs/evaluation.md`).
- [ ] Short recorded demo or walkthrough: you record it. A script and saved traces are in `docs/demo.md`. It must show a multi-document question, evidence-driven re-retrieval, a clarification and a failed tool call. **Caveat:** with the real model, the clarification does not trigger reliably (CASE-4). Show it with a question where it does, or say so openly.
- [x] Short summary of achievements, unfinished work and improvements (`docs/summary.md`).
- [~] Deployment runbook and evidence: runbook, Dockerfiles, Compose and CI are done; local evidence is saved (smoke test, restart persistence, Redis outage, health output).
- [ ] Still missing: a public HTTPS URL, immutable release tag and image digests, a public end-to-end check, an update and rollback drill.

## 6. Optional enhancements (not required)

- [x] Authentication: a demo passcode with per-session isolation. [x] Advanced retrieval: hybrid search, measured against alternatives.
- [ ] Infrastructure as code, Kubernetes: not attempted.

## What only you can do

1. Create the VM (or choose a host), point a domain, create a spend-capped OpenRouter key and set a strong `DEMO_PASSCODE`.
2. Open the pull requests, protect `main`, merge, let CI run, and tag the release.
3. Record the demo.
4. Do the manual citation review (about 20 cited pages) and fill the log.
5. Before the interview: be able to walk through the agent loop, the verifier and the retrieval choices, and make a small change live.

## Could be improved (ranked by value)

1. **Clarification and supersession in the agent.** Replace prompt rules with a structured field the code acts on, and compare document dates for conflicts. Targets CASE-4 and CASE-6.
2. **Vocabulary bridging for retrieval.** Query expansion from the documents' own terms. Targets CASE-9.
3. **A held-out question set**, so the evaluation is not tuned on itself.
4. **Cost of the agent.** It spends about eight times the tokens of the baseline; trimming tool results and reusing reads would cut that.
5. **Answer style.** Answers are long; shorter, scannable answers would read better.
6. **Production scale.** Background ingestion, object storage, single sign-on, tracing and cost dashboards.
