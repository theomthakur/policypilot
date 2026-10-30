# Submission checklist against the take-home brief

Status as of 30 Oct 2026, from the integrated branch (`integration/full-stack`). Legend: **[x] done** (built and verified by a test, a run or saved output), **[~] partial** (works, something named is open), **[ ] pending** (not done). The wording of each requirement is paraphrased from the brief.

## 1. The problem statement

- [x] Full-stack agentic RAG app over about 8 to 15 text PDFs from one domain. (10 synthetic university IT policies, 85 pages, plus 4 real public NIST documents: 14 PDFs, 231 pages.)
- [x] Users can upload documents and ask simple or multi-part questions.
- [x] The agent chooses tools, inspects results, and decides between retrieving more, asking for clarification, or answering with document and page citations.
- [~] Asking for clarification works in the code and in tests, but the real model does not reliably ask when it should (see CASE-4 below).
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
- [x] CI workflow (tests including integration, contract drift, image builds, secret scan, manifest renders, Compose smoke test) **passed on GitHub** for this branch ([run 41068139547](https://github.com/theomthakur/policypilot/actions/runs/41068139547)). It has not run on `main`: CI triggers on pull requests and `main`, and on this branch.
- [ ] Production images are not published; the production Compose file expects immutable images.
- [~] Update and rollback instructions are written (`docs/runbook.md`). A bad-image rollout and rollback was drilled on the Kubernetes path (`docs/deployment-evidence/2026-10-30/kind-drills.txt`); the Compose production path (VM, Caddy) has not been drilled.

**I. Evaluation**
- [x] Repeatable evaluation script with 11 cases, expected behavior and expected sources (`eval/run.py`, `eval/cases.yaml`).
- [x] Actual results and a failure analysis (`docs/evaluation.md`), compared with a single-pass retrieve-once baseline on the same corpus and model, with traces committed and exclusions explained (CASE-4 and CASE-8 are not applicable to the baseline).
- [x] The write-up says where iteration helps and where it only adds cost; the agent does not win every case.
- [~] Manual citation check: done for the last run by the assistant that built the system, not by a person (`docs/evaluation.md`: 21 of 21 claims have their numbers and terms on the cited page, and a read-through found them supported). Please spot-check about 20 cited pages yourself.

**J. Engineering quality**
- [x] Clear module layout, ADRs, 157 backend tests and 23 frontend tests, ruff and strict mypy, ESLint, TypeScript, Prettier.
- [x] Tests pass locally and in GitHub Actions.

## 3. Required test cases (three repeats, r15 to r17, agent vs baseline)

Each case records expected behavior, actual result, citations, pass or fail, tool calls, latency, tokens and a failure note in `eval/results/run-2026-10-29-gpt-4o-mini-r10/`.

- [x] 1 Simple lookup: pass, pass
- [x] 2 Multi-document A: pass, pass
- [x] 3 Multi-document B: agent 3 of 3, baseline 0 of 3 (it cites one document)
- [ ] 4 Ambiguous question: **fail** in 3 of 3 repeats (r15 to r17). The structured ambiguity check asks in some runs (r13, r14 asked, then answered) but not reliably; held-out HELD-4 also 0 of 2. Baseline not applicable.
- [x] 5 Insufficient evidence: **pass** in 3 of 3 repeats (explicit abstention, `missing_evidence` notice, no citations); the old strict wording check is kept as `legacy_checks`.
- [x] 6 Conflicting sources: **3 of 3** repeats after the conflict template (r15 to r17 before it: 1 of 3). When the question is about a superseded provision in force today and both documents were read, the answer is built from the two literal passages with a conflict notice; documented exceptions (service accounts) and historical questions are left alone. Baseline 0 of 3. The template is metadata-driven, so it helps only where a document states its own supersession.
- [x] 7 Prompt injection: pass, pass
- [x] 8 Tool failure or timeout: pass; baseline not applicable
- [ ] 9 Adaptive re-retrieval (extra): **fail** 0 of 3 (the answer cites the data-classification page but not the cloud-services page); held-out HELD-9, a similar vocabulary mismatch, passed 2 of 2 for the agent.
- [x] 10 One document, many parts (extra): pass, pass
- [~] 11 Follow-up question (extra): agent **2 of 3**, baseline 0 of 3 (the failed run searched the NIST incident document and ran out of searches).

Latest full run (30 Oct 2026, one run per set): tuned cases agent 9 of 11, baseline 4 of 9; 9 newer questions agent 9 of 9, baseline 5 of 7; 10 older held-out questions agent 6 of 10, baseline 5 of 9. No set is blind. The canonical result, the manual citation review and the limits are in `docs/evaluation.md`.

## 4. Technology

- [x] Redis and Docker are used and required; PostgreSQL; FastAPI; React and TypeScript; the whole stack runs through Docker Compose.
- [x] AI-assisted coding is allowed if you can explain the code. That part is yours: see "Before the interview" below.

## 5. What to submit

- [~] GitHub repository with implementation and setup instructions: code and README are on `integration/full-stack`; `main` still holds only the first commit, so open pull requests and merge.
- [x] Reproducibility notes: corpus source, model and embedding IDs, prompts, tool schemas, environment template, evaluation command, expected cost (`docs/reproducibility.md`).
- [x] System design and architecture diagram with components, agent states, tool calls, decision points, retrieval loop and stopping conditions (`docs/architecture.md`, `docs/system-design.md`, the in-app System design page).
- [x] Agent and baseline evaluation results and failure analysis (`docs/evaluation.md`).
- [ ] Short recorded demo or walkthrough: you record it. A script and saved traces are in `docs/demo.md`. It must show a multi-document question, evidence-driven re-retrieval, a clarification and a failed tool call. **Caveat:** with the real model the clarification does not trigger reliably (CASE-4 passed 0 of 3 repeats). Show it with a question where it does ("How do I renew my account?" asked and was answered in runs r13 and r14), or say so openly.
- [x] Short summary of achievements, unfinished work and improvements (`docs/summary.md`).
- [~] Deployment runbook and evidence: runbook, Dockerfiles, Compose and CI are done; local evidence is saved (smoke test, restart persistence, Redis outage, health output).
- [ ] Still missing: a public HTTPS URL, immutable release tag and image digests, a public end-to-end check, an update and rollback drill.

## 6. Optional enhancements (not required)

- [x] Authentication: OpenID Connect sign-in with per-user ownership (tested against Keycloak, [`docs/authentication.md`](authentication.md)); the demo passcode remains as a cost gate. [x] Advanced retrieval: hybrid search measured against alternatives, plus document-family discovery.
- [~] Infrastructure as code, Kubernetes: manifests and scripts for a local `kind` cluster, deployed and drilled ([`docs/kubernetes.md`](kubernetes.md), evidence in `docs/deployment-evidence/2026-10-30/`); single node, no autoscaler, NetworkPolicy and OpenShift not demonstrated.
- [x] Durable job queue and worker with crash recovery ([ADR 0010](adr/0010-durable-postgres-jobs.md)).

## What only you can do

1. Create the VM (or choose a host), point a domain, create a spend-capped OpenRouter key and set a strong `DEMO_PASSCODE`.
2. Open the pull requests, protect `main`, merge, let CI run, and tag the release.
3. Record the demo.
4. Do the manual citation review (about 20 cited pages) and fill the log.
5. Before the interview: be able to walk through the agent loop, the verifier and the retrieval choices, and make a small change live.

## Could be improved (ranked by value)

1. **Clarification.** A judge-model check with code gates now asks on genuinely ambiguous questions and rarely needlessly (fresh set), but misses CASE-4 and has only been measured on a few questions. Needs a larger, blind set and probably a better judge prompt.
2. **Vocabulary bridging for retrieval.** Query expansion from the documents' own terms. Targets CASE-9.
3. **A larger held-out set.** Three sets exist and none is blind; a fresh set of at least 20 questions, with repeats, would give an estimate that can be trusted.
4. **Cost of the agent.** It spends about eight times the tokens of the baseline; trimming tool results and reusing reads would cut that.
5. **Answer style.** Answers are long; shorter, scannable answers would read better.
6. **Production scale.** Object storage, university single sign-on, replicated database, tracing and cost dashboards. (Background jobs and sign-in now exist.)
