# Requirements and traceability

Every requirement has an ID. Pull requests reference the IDs they satisfy, and the **Status** column is updated when the work merges. Source: the assignment brief (sections 2 to 6).

Status values: `planned`, `in progress`, `done` (implemented and verified by a test, a run or a saved output), `partial` (works, but something named below is still open). Updated 1 Nov 2026 in the local working tree. The current evaluation facts are the **Final evaluated release** at the top of [`evaluation.md`](evaluation.md). D2 and I6 (independent human citation spot-check) stay partial. SUB-5 is complete through the reproducible walkthrough.

**What `partial` means here:** D2 is validated by Pydantic models, not by `contracts/tools.schema.json`. I6 has automatic quote verification, while independent human review is still pending. The current ten-case acceptance suite passed 30 of 30 Agent runs. SUB-5 is satisfied by the reproducible walkthrough in `docs/demo.md`; a recorded demo is optional because the brief accepts either form. Older run history is retained in `evaluation.md` but does not override its canonical block.

## Functional requirements

### A. Application architecture
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-A1 | Frontend and backend are separate deployable services | Two containers; the UI calls the backend only through `/api/v1` | done |
| REQ-A2 | A REST API layer connects the components | `contracts/openapi.yaml` describes every endpoint; contract test passes in CI | done |
| REQ-A3 | Clean, usable UI: upload, ask, read answers with citations, see the trace | Manual walkthrough of the demo script | done |

### B. RAG pipeline
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-B1 | Parse text-based PDFs page by page | Each corpus PDF produces one `document_pages` row per page | done |
| REQ-B2 | Chunk text without crossing page boundaries | Unit test: every chunk has exactly one page number | done |
| REQ-B3 | Index chunks for vector and full-text search | HNSW and GIN indexes exist; hybrid search returns expected pages for 5 known queries | done |
| REQ-B4 | Retrieve with document and page metadata preserved | Every search result carries document ID, title and page | done |
| REQ-B5 | Generate answers grounded in sources, cited by document and page | Every claim in an answer cites at least one (document, page) | done |
| REQ-B6 | Users can upload PDFs | `POST /api/v1/documents` ingests a new PDF; it becomes searchable | done |

### C. Adaptive agent orchestration
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-C1 | An LLM-driven tool-use loop, not a fixed retrieve-then-generate sequence | Trace shows the model choosing tools across multiple steps | done |
| REQ-C2 | Decompose multi-part questions | Trace shows sub-questions for CASE-2 and CASE-3 | done |
| REQ-C3 | Revise queries after weak results | The scripted test `test_weak_search_triggers_a_visible_revised_query` shows a weak search followed by a revised query. In real-model runs the agent mostly revises to cover a part of the question the first results missed (CASE-3) | done |
| REQ-C4 | Combine evidence across documents | CASE-2 and CASE-3 cite at least two documents | done |
| REQ-C5 | Decide between retrieving more, asking for clarification, or answering | CASE-5 states missing evidence; CASE-1 answers; clarification has separate integration coverage | done |
| REQ-C6 | At least one result-driven change of action is demonstrated | Saved trace for CASE-3 (`docs/demo-evidence/02-re-retrieval.md`): the first search leaves one part unanswered, the agent searches again for it and reads two full pages; CASE-8 retries a failed search | done |

### D. Tool contracts
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-D1 | At least three distinct read-only tools | `list_documents`, `search_documents`, `read_document_pages` implemented | done |
| REQ-D2 | Structured input and output | Inputs and outputs validate against `contracts/tools.schema.json` | partial |
| REQ-D3 | Argument validation | Unit tests: invalid arguments return `INVALID_ARGUMENT` | done |
| REQ-D4 | Empty-result handling | Unit test: no match returns `status: empty` with a suggestion | done |
| REQ-D5 | Error handling | Unit tests for not found, not ready, out of range, timeout, dependency unavailable | done |

### E. State and observability
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-E1 | Per-session question, tool-result, evidence and clarification state | Integration test: a clarification is stored and resumed | done |
| REQ-E2 | UI execution trace with tool names, inputs, result summaries, status and citations | Trace panel shows every event in `contracts/trace-event.schema.json` | done |
| REQ-E3 | Record timing and token usage | Each turn stores latency, prompt and completion tokens and estimated cost | done |
| REQ-E4 | No private chain-of-thought exposed | Trace contains actions and summaries only | done |

### F. Execution safety
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-F1 | Configurable step limit | Agent test: the limit produces `stop_reason: limit_steps` and a partial answer | done |
| REQ-F2 | Tool timeouts | Agent test: a slow tool returns `TIMEOUT` | done |
| REQ-F3 | Bounded retries | CASE-8: exactly one retry, then a graceful result | done |
| REQ-F4 | Useful partial responses on limits | Partial answers include verified findings and say what's missing | done |
| REQ-F5 | Retrieved instructions treated as untrusted | CASE-7: injected text never followed; flagged in the trace | done |
| REQ-F6 | Tools restricted to the corpus | Tools accept only document IDs visible to the session; no paths or URLs | done |
| REQ-F7 | Isolated sessions | Integration test: session B can't see session A's uploads or turns | done |

### G. Persistence and Redis
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-G1 | Persistent database | Data survives `docker compose restart` (persistence script) | done |
| REQ-G2 | Redis has a real purpose | Session state, search cache, ingestion progress, rate limits, daily budget | done |
| REQ-G3 | Keys, expiry and invalidation documented | `docs/redis.md` | partial |
| REQ-G4 | Defined behavior when Redis is unavailable | Outage script: questions still work; readiness reports `degraded` | done |
| REQ-G5 | Redis usage demonstrated | Demo and saved output of the outage script | done |

### H. Containerization and DevOps
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-H1 | Dockerfiles for frontend and backend | Images build in CI | done |
| REQ-H2 | Docker Compose for frontend, backend, Redis and Postgres | `docker compose up` brings all services to healthy | done |
| REQ-H3 | Environment configuration and secrets handling | `.env.example` without secrets; `.env` git-ignored | done |
| REQ-H4 | Health checks and volumes | Every service has a health check; named volumes for data | done |
| REQ-H5 | CI runs tests and image builds | GitHub Actions green on `integration/full-stack` | done |
| REQ-H6 | Smoke test, persistence across restart, Redis outage behavior | Scripts and saved output | done |
| REQ-H7 | Update and rollback instructions | `docs/runbook.md` | done |

### I. Evaluation
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-I1 | Repeatable evaluation script with at least eight cases | `make eval` runs CASE-1 to CASE-10 | done |
| REQ-I2 | Expected behavior and sources per case | `eval/cases.yaml` | done |
| REQ-I3 | Actual results and failure analysis | `docs/evaluation.md` | done |
| REQ-I4 | Comparison with a single-pass baseline on the same corpus and model | Report has agent and baseline columns | done |
| REQ-I5 | Representative traces and explained exclusions | Saved traces; n/a cases explained | done |
| REQ-I6 | Citation verification against actual supporting passages | Automated check plus a manual page-check log | partial |

### J. Engineering quality
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-J1 | Clear code organization | Module boundaries per `docs/system-design.md` | done |
| REQ-J2 | Tests, linting and type checks | CI required checks | done |
| REQ-J3 | Documentation | Every file in the documentation set exists and cites the canonical r31 evaluation record | done |

### I. Added 30 Oct 2026 (beyond the brief's required scope)
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-I1 | Real sign-in (OpenID Connect) with revocable server-side sessions | `tests/integration/test_auth.py`; Keycloak browser run in the deployment evidence | done (not tried against a university provider) |
| REQ-I2 | Every conversation, upload and trace belongs to one user | two-user isolation test and browser run | done |
| REQ-I3 | Accepted questions and uploads survive process restarts | `tests/integration/test_jobs.py`; worker SIGKILL drill | done |
| REQ-I4 | Document authority, version, effective date and documented supersession reach retrieval and the conflict notice | `tests/integration/test_p1_agent.py` | done |
| REQ-I5 | A held-out evaluation set, reported separately from the tuned cases | `eval/heldout.yaml`, `docs/evaluation.md` | done |
| REQ-I6 | A second, tested deployment path on Kubernetes | `scripts/k8s_*.sh`, `docs/deployment-evidence/2026-10-30/` | partial (single node, single replicas; NetworkPolicy and OpenShift not demonstrated) |

## Evaluation cases

| ID | Case | Observable pass criterion | Status |
|---|---|---|---|
| CASE-1 | Simple lookup | Directly supported fact; correct passage and page cited | done |
| CASE-2 | Multi-part, multi-document A | All parts answered using evidence from at least two documents | done |
| CASE-3 | Multi-part, multi-document B | A second distinct cross-document question; each supported claim cited | done |
| CASE-4 | Defined student-account renewal lookup | Automatic renewal, no student action, with the account-lifecycle page cited | done (3 of 3 1 Nov acceptance runs; not blind) |
| CASE-5 | Insufficient evidence | States evidence is missing; no fabricated answer or citation | done |
| CASE-6 | Conflicting sources | Identifies and cites both passages; explains uncertainty without silently choosing | done (3 of 3 r31 tuned runs; not blind) |
| CASE-7 | Prompt injection in a document | Ignores malicious instructions; answers only from trusted instructions and evidence | done |
| CASE-8 | Tool failure or timeout | Bounded retry or graceful recovery; stops within limits; reports incomplete work | done |
| CASE-9 | Multi-part, single document (extra) | All parts answered from one document | done (3 of 3 1 Nov acceptance runs; not blind) |
| CASE-10 | Multi-turn follow-up (extra) | Second question resolved from the first turn's context | done (3 of 3 1 Nov acceptance runs; not blind) |

## Submission items

| ID | Item | Location | Status |
|---|---|---|---|
| SUB-1 | Repository with implementation and setup instructions | `README.md` | done |
| SUB-2 | Reproducibility notes: corpus, model and embedding IDs, prompts, tool schemas, env template, eval command, expected API cost | `docs/reproducibility.md` | done |
| SUB-3 | Architecture diagram: components, agent state, tool calls, decision points, retrieval loop, stopping conditions | `docs/system-design.md` | done |
| SUB-4 | Agent and baseline evaluation results and failure analysis | `docs/evaluation.md`, `eval/results/` | done |
| SUB-5 | Demo or walkthrough: multi-document question, evidence-driven re-retrieval, clarification, failed tool call; saved traces | [Demo video](https://youtu.be/njw7qmk8aTQ), `docs/demo.md`, `docs/demo-evidence/` (re-retrieval, clarification and the failed tool call are saved traces, not live in the video) | done |
| SUB-6 | Summary of achievements, unfinished work and improvements | `docs/summary.md` | done |
| SUB-7 | Deployment runbook and evidence | `docs/runbook.md`, `docs/deployment-evidence/` | done |
