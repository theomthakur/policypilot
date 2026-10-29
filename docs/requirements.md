# Requirements and traceability

Every requirement has an ID. Pull requests reference the IDs they satisfy, and the **Status** column is updated when the work merges. Source: the assignment brief (sections 2 to 6).

Status values: `planned`, `in progress`, `done`, `partial` (explained in `docs/summary.md`).

## Functional requirements

### A. Application architecture
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-A1 | Frontend and backend are separate deployable services | Two containers; the UI calls the backend only through `/api/v1` | planned |
| REQ-A2 | A REST API layer connects the components | `contracts/openapi.yaml` describes every endpoint; contract test passes in CI | planned |
| REQ-A3 | Clean, usable UI: upload, ask, read answers with citations, see the trace | Manual walkthrough of the demo script | planned |

### B. RAG pipeline
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-B1 | Parse text-based PDFs page by page | Each corpus PDF produces one `document_pages` row per page | planned |
| REQ-B2 | Chunk text without crossing page boundaries | Unit test: every chunk has exactly one page number | planned |
| REQ-B3 | Index chunks for vector and full-text search | HNSW and GIN indexes exist; hybrid search returns expected pages for 5 known queries | planned |
| REQ-B4 | Retrieve with document and page metadata preserved | Every search result carries document ID, title and page | planned |
| REQ-B5 | Generate answers grounded in sources, cited by document and page | Every claim in an answer cites at least one (document, page) | planned |
| REQ-B6 | Users can upload PDFs | `POST /api/v1/documents` ingests a new PDF; it becomes searchable | planned |

### C. Adaptive agent orchestration
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-C1 | An LLM-driven tool-use loop, not a fixed retrieve-then-generate sequence | Trace shows the model choosing tools across multiple steps | planned |
| REQ-C2 | Decompose multi-part questions | Trace shows sub-questions for CASE-2 and CASE-3 | planned |
| REQ-C3 | Revise queries after weak results | CASE-9 trace shows a weak search followed by a revised query or page read | planned |
| REQ-C4 | Combine evidence across documents | CASE-2 and CASE-3 cite at least two documents | planned |
| REQ-C5 | Decide between retrieving more, asking for clarification, or answering | CASE-4 asks; CASE-5 states missing evidence; CASE-1 answers | planned |
| REQ-C6 | At least one result-driven change of action is demonstrated | Saved trace for CASE-9 | planned |

### D. Tool contracts
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-D1 | At least three distinct read-only tools | `list_documents`, `search_documents`, `read_document_pages` implemented | planned |
| REQ-D2 | Structured input and output | Inputs and outputs validate against `contracts/tools.schema.json` | planned |
| REQ-D3 | Argument validation | Unit tests: invalid arguments return `INVALID_ARGUMENT` | planned |
| REQ-D4 | Empty-result handling | Unit test: no match returns `status: empty` with a suggestion | planned |
| REQ-D5 | Error handling | Unit tests for not found, not ready, out of range, timeout, dependency unavailable | planned |

### E. State and observability
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-E1 | Per-session question, tool-result, evidence and clarification state | Integration test: a clarification is stored and resumed | planned |
| REQ-E2 | UI execution trace with tool names, inputs, result summaries, status and citations | Trace panel shows every event in `contracts/trace-event.schema.json` | planned |
| REQ-E3 | Record timing and token usage | Each turn stores latency, prompt and completion tokens and estimated cost | planned |
| REQ-E4 | No private chain-of-thought exposed | Trace contains actions and summaries only | planned |

### F. Execution safety
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-F1 | Configurable step limit | Agent test: the limit produces `stop_reason: limit_steps` and a partial answer | planned |
| REQ-F2 | Tool timeouts | Agent test: a slow tool returns `TIMEOUT` | planned |
| REQ-F3 | Bounded retries | CASE-8: exactly one retry, then a graceful result | planned |
| REQ-F4 | Useful partial responses on limits | Partial answers include verified findings and say what's missing | planned |
| REQ-F5 | Retrieved instructions treated as untrusted | CASE-7: injected text never followed; flagged in the trace | planned |
| REQ-F6 | Tools restricted to the corpus | Tools accept only document IDs visible to the session; no paths or URLs | planned |
| REQ-F7 | Isolated sessions | Integration test: session B can't see session A's uploads or turns | planned |

### G. Persistence and Redis
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-G1 | Persistent database | Data survives `docker compose restart` (persistence script) | planned |
| REQ-G2 | Redis has a real purpose | Session state, search cache, ingestion progress, rate limits, daily budget | planned |
| REQ-G3 | Keys, expiry and invalidation documented | `docs/redis.md` | planned |
| REQ-G4 | Defined behavior when Redis is unavailable | Outage script: questions still work; readiness reports `degraded` | planned |
| REQ-G5 | Redis usage demonstrated | Demo and saved output of the outage script | planned |

### H. Containerization and DevOps
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-H1 | Dockerfiles for frontend and backend | Images build in CI | planned |
| REQ-H2 | Docker Compose for frontend, backend, Redis and Postgres | `docker compose up` brings all services to healthy | planned |
| REQ-H3 | Environment configuration and secrets handling | `.env.example` without secrets; `.env` git-ignored | planned |
| REQ-H4 | Health checks and volumes | Every service has a health check; named volumes for data | planned |
| REQ-H5 | CI runs tests and image builds | GitHub Actions green on `main` | planned |
| REQ-H6 | Smoke test, persistence across restart, Redis outage behavior | Scripts and saved output | planned |
| REQ-H7 | Update and rollback instructions | `docs/runbook.md` | planned |

### I. Evaluation
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-I1 | Repeatable evaluation script with at least eight cases | `make eval` runs CASE-1 to CASE-11 | planned |
| REQ-I2 | Expected behavior and sources per case | `eval/cases.yaml` | planned |
| REQ-I3 | Actual results and failure analysis | `docs/evaluation.md` | planned |
| REQ-I4 | Comparison with a single-pass baseline on the same corpus and model | Report has agent and baseline columns | planned |
| REQ-I5 | Representative traces and explained exclusions | Saved traces; n/a cases explained | planned |
| REQ-I6 | Citation verification against actual supporting passages | Automated check plus a manual page-check log | planned |

### J. Engineering quality
| ID | Requirement | Acceptance test | Status |
|---|---|---|---|
| REQ-J1 | Clear code organization | Module boundaries per `docs/architecture.md` | planned |
| REQ-J2 | Tests, linting and type checks | CI required checks | planned |
| REQ-J3 | Documentation | Every file in the documentation set exists | planned |

## Evaluation cases

| ID | Case | Observable pass criterion | Status |
|---|---|---|---|
| CASE-1 | Simple lookup | Directly supported fact; correct passage and page cited | planned |
| CASE-2 | Multi-part, multi-document A | All parts answered using evidence from at least two documents | planned |
| CASE-3 | Multi-part, multi-document B | A second distinct cross-document question; each supported claim cited | planned |
| CASE-4 | Ambiguous question | Targeted clarification instead of a guess; context kept in the follow-up | planned |
| CASE-5 | Insufficient evidence | States evidence is missing; no fabricated answer or citation | planned |
| CASE-6 | Conflicting sources | Identifies and cites both passages; explains uncertainty without silently choosing | planned |
| CASE-7 | Prompt injection in a document | Ignores malicious instructions; answers only from trusted instructions and evidence | planned |
| CASE-8 | Tool failure or timeout | Bounded retry or graceful recovery; stops within limits; reports incomplete work | planned |
| CASE-9 | Adaptive re-retrieval (extra) | Weak first search, then a revised action, then a grounded answer | planned |
| CASE-10 | Multi-part, single document (extra) | All parts answered from one document | planned |
| CASE-11 | Multi-turn follow-up (extra) | Second question resolved from the first turn's context | planned |

## Submission items

| ID | Item | Location | Status |
|---|---|---|---|
| SUB-1 | Repository with implementation and setup instructions | `README.md` | planned |
| SUB-2 | Reproducibility notes: corpus, model and embedding IDs, prompts, tool schemas, env template, eval command, expected API cost | `docs/reproducibility.md` | planned |
| SUB-3 | Architecture diagram: components, agent state, tool calls, decision points, retrieval loop, stopping conditions | `docs/architecture.md` | planned |
| SUB-4 | Agent and baseline evaluation results and failure analysis | `docs/evaluation.md`, `eval/results/` | planned |
| SUB-5 | Demo or walkthrough: multi-document question, evidence-driven re-retrieval, clarification, failed tool call; saved traces | `docs/demo.md` | planned |
| SUB-6 | Summary of achievements, unfinished work and improvements | `docs/summary.md` | planned |
| SUB-7 | Deployment runbook and evidence | `docs/runbook.md`, `docs/deployment-evidence/` | planned |
