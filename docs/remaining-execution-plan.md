# PolicyPilot: remaining execution plan

Status: proposed work only. No application changes are implemented by this document.

Baseline reviewed: `integration/full-stack`, commit `0bc1d99583f32b704c27b644fe404902a3768920`.
Prepared October 29, 2026, America/New_York.
Submission deadline: Sunday, November 1, 2026, noon New York time. Interview: Monday, November 2, 11:00–12:00 New York time.

## 1. Outcome and priorities

Deliver a working, explainable agentic RAG application with all required scenarios demonstrated, real authentication, and a reproducible Kubernetes deployment. Keep Docker Compose as the required, independently working deployment path. Kubernetes and authentication are explicit scope requested by Om, although the assignment calls them optional.

Order of importance: correct evidence and adaptive behavior; safe authentication and isolation; reliable deployment and recovery; credible evaluation; clear presentation. The existing visual identity should be preserved. Avoid another redesign or framework migration.

Use this plan as an implementation handoff. Inspect the current branch before starting: another implementer may already have addressed a task. A task is complete only when its acceptance evidence exists. Do not replace real evaluation failures with claims or hardcoded answers.

## 2. Source of truth and verified baseline

Primary requirements: `Take-Home Assignment _ Agentic RAG Application .pdf`, five pages, supplied by NYU IT. Page 3 defines architecture/RAG/agent/tools; page 4 defines state/safety/persistence/DevOps/evaluation and cases 1–6; page 5 defines cases 7–8, submission artifacts and optional enhancements.

The assignment's interview schedule is 5 minutes introduction, 20 minutes take-home, 30 minutes system design, 5 minutes questions. Use these durations for preparation.

Current implementation:

- React/TypeScript frontend, FastAPI backend, PostgreSQL/pgvector and Redis.
- Ten synthetic policy PDFs plus four public NIST reference PDFs. Keep their authority and provenance distinct.
- Four read-only tools: `list_documents`, `search_documents`, `read_document_pages`, `get_document_outline`.
- Explicit bounded agent loop, evidence ledger, literal citation verification, persisted turns/traces, session cookie isolation, Redis cache/fallback, Docker Compose and CI configuration.
- Backend lint/type checks passed; 27 tests passed and 2 external integration tests skipped locally. Frontend formatting/lint, 16 tests and build passed. Evaluation contract validates 11 cases. These are prior audit results, not proof of any future change.
- Docker configuration parsed, but the Docker daemon was unavailable during the audit. Historical deployment evidence must be repeated against the submitted commit.
- Latest recorded real-model evaluation r10: agent 6/11; baseline 5/9 applicable cases. Required agent cases 1, 2, 3, 7, 8 pass; 4, 5, 6 fail. Additional cases 9 and 11 fail; case 10 passes. Reference: `docs/evaluation.md`.

Observed implementation dependencies relevant to this plan:

- `backend/app/turns/service.py` starts turns with in-process `asyncio.create_task`; losing a process can interrupt work.
- Upload ingestion uses API background tasks; corpus autoload runs during API startup.
- `backend/start.sh` runs migrations on each API start. Multiple replicas would introduce migration/startup coordination concerns.
- Uploaded PDF bytes are on a local filesystem. Increasing replicas alone does not provide shared storage.
- A conversation UUID cookie and shared demo passcode are not user authentication. No user ownership model exists in `db/models.py`.
- Search uses PostgreSQL full-text search plus dense vectors with RRF. Call this PostgreSQL full-text retrieval, not BM25.
- Tool invocations and retry attempts need separate metrics. The current retry loop counts a logical call once, while traces contain individual attempts.

## 3. Work packages and dependencies

| ID | Work | Priority | Depends on | Completion evidence |
|---|---|---|---|---|
| P0 | Freeze baseline, inspect traces, agree contracts | First | None | Baseline SHA, failures, documented schemas |
| P1 | Clarification, missing evidence, conflict, adaptive retrieval and follow-up repairs | Required | P0 | Required cases pass; additional regressions improve |
| P2 | Authentication and ownership | Requested enhancement | P0 | Real login/logout and two-user isolation tests |
| P3 | Durable work, restart recovery, storage and deployment boundaries | Required for credible orchestration | P0; integrate P2 ownership | Restart/duplicate-delivery/outage tests |
| P4 | Kubernetes, OpenShift compatibility and Compose parity | Requested enhancement | P2 and P3 contracts stable | Running cluster and captured drills |
| P5 | Final evaluation, citation review, performance and accessibility | Required | P1–P4 integrated | Raw results, held-out results, manual source checks |
| P6 | Docs, demo, release and submission package | Required | P5 | Fresh checkout walkthrough, submitted artifacts |

Other LLMs may work on isolated branches, but assign one owner to each shared contract. Agent/retrieval changes share `tools/contracts.py`, agent state and eval contracts. Auth and infrastructure share migrations, ownership, configuration and health routes. Agree these interfaces before simultaneous edits. Integrate one package at a time and rerun affected checks.

## 4. P0 — establish the baseline

1. Record branch, SHA, corpus hashes, prompt version, model/embedding identifiers and configuration. Preserve r10 outputs unchanged.
2. Read the raw failing traces, not only their summaries. Classify each failure as retrieval, decision, synthesis, citation, evaluator or runtime error. The existing analysis contains hypotheses; confirm them before selecting a fix.
3. Freeze the eight mandatory cases. Keep existing extra cases. Add held-out paraphrases and new questions before tuning further; do not inspect their answers to tune prompts.
4. Agree additional schemas for clarification, per-subquestion evidence coverage, source authority/version metadata, authentication and durable jobs.
5. Establish one reproducible root command that bootstraps its prerequisites. The current `make test` assumes a root `.venv`; either make setup explicit or remove that hidden prerequisite.

Acceptance: a developer can reproduce the baseline failures and distinguish structural tests, fake-model tests, real-model evaluations and deployment drills.

## 5. P1 — repair required agent behavior

### P1-A: ambiguity and clarification, CASE-4

Problem: the model answers for all account types instead of asking which type applies. More prompt wording has already been tried and has not reliably fixed it.

Implementation:

- Extend the planning/control schema with validated fields such as `answerable`, `missing_slots`, `candidate_interpretations`, `clarification_question`, and subquestions. Keep output concise and observable; do not request private reasoning.
- Ask for clarification when a missing user attribute changes the recommended action and is not supplied in history. Do not ask when the requested fact is universal or the user explicitly requests all alternatives.
- Allow initial retrieval to discover that different procedures exist. A structured post-retrieval assessment should identify material ambiguity; the loop then executes the clarification action rather than trusting an optional prose suggestion.
- Persist the original question, pending clarification, choices, turn ID and resolved slots. On reply, combine the original question with the supplied account type and resume retrieval.
- Support free-text replies as well as choices. If a reply does not resolve the missing slot, ask a targeted follow-up within a bounded clarification policy.
- Keep history per authenticated user and conversation. Test reload and Redis-outage recovery from PostgreSQL.

Primary files: `backend/app/tools/contracts.py`, `backend/app/agent/state.py`, `backend/app/agent/loop.py`, `backend/app/turns/service.py`, session state, tool/API schemas; `frontend/src/components/ClarificationCard.tsx` and API types if the contract changes.

Acceptance: CASE-4 asks account type before giving a procedure, then answers the sponsored-guest follow-up with the correct page. Add at least three unseen ambiguous phrasings and three already-specific questions that must not trigger clarification. No matching against CASE IDs or exact question strings.

### P1-B: insufficient evidence, CASE-5

Problem: r10's response expresses missing evidence, but its wording fails a regex; an earlier run also lacked a required notice.

Implementation:

- Normalize the final response contract for `insufficient_evidence`: an explicit user-facing missing-evidence statement, a structured `missing_evidence` notice, no invented amount, and no citation presented as supporting the absent fact.
- Distinguish no relevant topic, relevant topic with missing fact, and partial evidence for some subquestions. For a partial answer, cite supported claims and mark only the unsupported portions incomplete.
- Evaluate the structured stop reason, notice, absence of unsupported claims and citation behavior. Retain a broad wording check for an explicit abstention rather than a brittle exact sentence.
- Manually adjudicate previously failed outputs before changing the evaluator. Preserve the old score and label a corrected score separately. Apply the same criteria to agent and baseline.

Acceptance: CASE-5 plus at least three new absent facts abstain explicitly without invented figures/citations. A supported similar question still answers normally. Never make a test pass merely by deleting its substantive criterion.

### P1-C: conflicting and superseded policies, CASE-6

Problem: the old password document is retrieved, while the newer identity standard is missed. A recent date alone does not establish authority or supersession.

Implementation:

- Carry source metadata from verified sidecars/manifests into stored documents and tool responses: issuer/domain, document family, effective date, version, authority type and explicit supersedes relationships where supported. Do not create relations by guessing from filenames.
- Add document-level discovery before chunk ranking when answering current policy questions. Search related titles, outlines and policy families; retrieve both relevant versions even if only one initially matches the question's wording.
- Keep both passages in the evidence ledger. Produce a conflict notice with both citations and explain the documented relationship. Without explicit precedence, state the conflict and uncertainty; do not silently choose the newer file.
- Distinguish institutional policy from NIST reference guidance. NIST material should not override a fictional university's concrete procedures or contact details.
- Treat metadata imported from user uploads as untrusted descriptive input; it cannot grant permissions or administrative authority.

Primary files: document models/migrations, corpus sidecars and ingestion, `retrieval/hybrid.py`, tool outputs, agent assessment and verifier; update contracts and evidence display together.

Acceptance: CASE-6 cites both dated passages, explains the disagreement and supported supersession. Add independent unresolved-conflict and historical-as-of-date cases. Verify the runtime does not read evaluation `expected_pages` or `cases` metadata as retrieval hints.

### P1-D: evidence-driven re-retrieval, CASE-9

Problem: high semantic similarity is being mistaken for sufficient support; everyday language misses policy vocabulary.

Implementation:

- Track evidence coverage per subquestion: supported, ambiguous, missing or conflicting, with evidence IDs. Similarity is a retrieval signal, not a correctness score.
- After each result, use a structured evidence assessment to choose read-page, discover-documents, rewrite-query, clarify, answer or abstain.
- Rewrite using terms found in titles, outlines and results; preserve user intent. Document-scoped follow-up search can reduce irrelevant reference material.
- Keep existing hybrid retrieval. Measure retrieval recall before adding a reranker or another dependency. A reranker is conditional on demonstrated improvement on held-out data.
- Preserve a real trace showing initial weak/incomplete evidence, a changed query/action, new evidence and a supported final answer. Empty-result fault injection can test the loop, but a natural example is also needed.

Acceptance: CASE-9 and fresh vocabulary-mismatch questions retrieve the right policy families. A direct lookup remains efficient. Never force an extra search solely to make a trace look agentic.

### P1-E: contextual follow-ups, CASE-11

Problem: a pronoun follow-up loses the relevant incident context and searches competing reference material.

Implementation:

- Store a bounded structured conversation summary with resolved subject, relevant document IDs, cited pages and unresolved subquestions. Previous generated answers are context, not new factual evidence.
- Rewrite a follow-up into a standalone search query using that context. Resolve role/entity when unambiguous; ask when multiple antecedents fit.
- Prefer previously relevant document IDs for the first follow-up search, with a corpus-wide fallback when evidence is absent. Retrieve and cite the actual contact passage.
- Bound history size and do not carry unrelated evidence across sessions or users.

Acceptance: CASE-11, reload, ambiguous-pronoun and unrelated-new-topic tests. Trace exposes the standalone query and source filters without private reasoning.

### P1-F: hard limits and truthful metrics

- Make tool calls, actual attempts, retries, blocked duplicates and model requests separate counters. Report both logical calls and actual attempts, with one definition shared by UI and evaluator.
- Apply the remaining turn deadline to each tool, model call, retry and backoff. A fixed tool timeout must not allow work to run beyond the turn's remaining time.
- Include planning/assessment/repair calls in token and cost accounting. Record estimated versus provider-reported usage distinctly, including failed requests where usage is known.
- Test maximum-step, token, tool-attempt and elapsed-time stops. A useful partial response must name missing work and cite only acquired evidence.
- Keep injection tests, parameter-validation tests, and corpus restrictions passing after all changes. Treat instruction detection as a supplemental signal, not the security boundary.

## 6. P2 — real authentication and authorization

Decision: standards-based OIDC login with a backend-managed browser session. Use an established OIDC client library; use Keycloak as a reproducible local provider profile or a configured hosted OIDC issuer for the deployed demo. University SSO integration is a future integration unless credentials/configuration are actually provided.

Scope:

1. Add `User` with immutable `(issuer, subject)` identity and `AuthSession` with a random opaque token stored as a hash, expiry and revocation. Add `owner_user_id` to conversations and enforce ownership through the entire data path. Define a migration for existing anonymous records; do not automatically grant them to the next person who logs in.
2. Implement login, callback, current-user and logout routes using Authorization Code with PKCE, state and nonce. Validate issuer/audience/signature/expiry through the client library. Keep provider tokens and client secret on the backend.
3. Put an HttpOnly, Secure-in-production, SameSite cookie on the browser. Add origin/CSRF protection for state-changing requests. Use same-origin frontend/API routing so SSE and PDF access inherit the authenticated session.
4. Authorize listing, upload, file download, page text, ingestion progress, sessions, turns, traces, polling and SSE. Browser-supplied conversation IDs are identifiers, never proof of ownership. Check authentication expiry and logout for established streams as well as new requests.
5. Shared corpus remains readable to signed-in users. Private uploads remain scoped to their owning user and, initially, their original conversation; cross-conversation reuse requires an explicit ACL change. An admin role may manage shared-corpus ingestion; it must not automatically expose private conversations.
6. Scope Redis/search keys and rate limits to authenticated access scope, conversation, corpus version and relevant retrieval configuration. A user can never receive cached material from another user.
7. Add a clear sign-in state, account menu, logout, expired-session handling and conversation restoration. Keep this small and visually consistent. A shared demo passcode may remain an operational gate, but cannot substitute for identity.
8. Production startup must fail closed when auth configuration is missing. Any fake-auth mode is test-only and rejected in production. Evaluation uses provisioned test identities or valid machine credentials; do not add an unauthenticated eval bypass.

Acceptance tests:

- Successful login/logout; wrong state/nonce, expired session, invalid issuer/audience/signature, revocation, provider outage and CSRF rejection.
- User A uploads a unique marker; User B cannot find it through search, cache, list, page, PDF, trace, direct ID or SSE endpoints. Repeat with Redis unavailable.
- User A can restore their own conversation after logout/login. Deleting a session cookie cannot turn a foreign UUID into an authorized session.
- Login and full question/upload flow work in both Compose and Kubernetes. No credentials or tokens in source, URLs shown in traces, frontend storage, screenshots or logs.

Planned files: `backend/app/auth/`, auth routes, models/migrations, `api/deps.py`, visibility filters, API/tool contracts, frontend auth components/API client, `.env.example`, Compose identity-provider profile and `docs/authentication.md`.

## 7. P3 — restart recovery, storage and orchestration prerequisites

Choose a small durable PostgreSQL job table for turns and ingestion. PostgreSQL is already required; this avoids making a Redis outage prevent all work while Redis continues its real caching/session role.

- Persist jobs transactionally with the API action. A separate worker claims jobs with row locking, leases and a heartbeat. Store attempts, deadline, last error, owner scope and terminal status.
- Claim atomically; use a lease/fencing version so an expired worker cannot overwrite a replacement worker's result. Serialize conflicting work per conversation or use optimistic state versions.
- On crash, reclaim or explicitly terminate stale work within a documented interval. Re-execution is bounded and visible. Model calls may repeat after a crash; do not claim exactly-once provider execution or billing.
- Use idempotency keys for repeated API submissions and one final result per turn. Define how incomplete trace attempts are represented on recovery.
- Stop claiming work on shutdown and drain or release jobs within the pod termination window. Surface queued/running/retrying/interrupted states in the UI.
- Run database migrations as a controlled deployment Job and corpus ingestion as an idempotent versioned seed Job. Concurrent API starts must not race to migrate or seed.
- Package the shared corpus in a versioned image/build artifact; do not depend on host bind mounts or fit PDFs into ConfigMaps.
- Introduce an upload-storage interface. Local filesystem remains available for single-instance Compose. For API/worker on independent nodes or multiple API replicas, use shared object storage or a verified RWX volume. An S3-compatible adapter with a local MinIO profile is a reproducible option. Put keys, checksums and ownership metadata in PostgreSQL; authorize downloads through the backend. If only RWO storage is implemented, constrain topology/replicas explicitly and do not claim multi-node scaling.

Acceptance: kill API during a request, kill worker during ingestion, deliver a job twice, restart the full stack, stop Redis, reconnect SSE and restore an upload. No silently stuck running records, duplicate final answers, partial searchable documents or lost PDF bytes. Database unavailability should prevent unsafe new work and return an actionable error.

## 8. P4 — Kubernetes that actually runs

Deliver a Kustomize base plus local `kind` overlay, with an OpenShift overlay if access permits. Preserve full Docker Compose parity. Do not treat successful YAML rendering as deployment evidence.

Resources and configuration:

- Namespace, service accounts, ConfigMaps for nonsecret configuration and Secret references. Generate secrets outside version control; do not commit demo passwords or encoded secrets.
- Frontend and API Deployments/Services; worker Deployment after P3; ingress routing `/` and `/api` to the same origin, with streaming timeouts and buffering disabled. Correct callback URL and HTTPS cookie settings for auth.
- PostgreSQL/pgvector and Redis StatefulSets with PVCs for the local demonstration, or managed dependencies for a hosted cluster. Single-replica StatefulSets provide persistence, not database replication or high availability.
- One-shot migration and corpus seed Jobs with clear ordering. Mount/bake the final 14-document corpus and version it with the release.
- Startup/liveness/readiness probes with different purposes. Redis outage is a degraded service condition where PostgreSQL fallback works; database failure removes serving readiness. Health endpoints must not spend LLM tokens.
- Measured resource requests/limits, worker concurrency, termination grace period and structured logs. Consider embedding-model startup memory and preload time.
- Nonroot execution, dropped capabilities, no privilege escalation and writable volumes only where needed. OpenShift arbitrary-UID behavior must be tested; remove fixed-UID/privileged assumptions.
- NetworkPolicy rules for actual permitted connections. Explain the cluster/CNI dependency. Standard NetworkPolicy does not provide a portable hostname allowlist for OpenRouter; document HTTPS egress and stronger controls available in the target environment.
- Backend HPA only after shared storage, durable work and concurrency tests pass; include Metrics Server prerequisite and load evidence. Otherwise keep one API replica, state the limit, and include the measured scaling design. Frontend replicas alone are simpler but do not demonstrate backend scaling.
- Rolling deployment, rollback, bad-image rejection, backup/restore and storage-retention instructions. Application rollback and database rollback are separate operations; use compatible migrations and avoid automatic destructive downgrades.

Planned artifacts:

```text
deploy/k8s/base/
deploy/k8s/overlays/kind/
deploy/k8s/overlays/openshift/
scripts/k8s_smoke.sh
scripts/k8s_recovery.sh
docs/kubernetes.md
docs/deployment-evidence/<release>/
```

Acceptance: a fresh local cluster starts from documented commands; all workloads become healthy; real login, upload, agent question, citations and traces work through ingress. Delete API/worker/Redis/PostgreSQL pods and show documented recovery/persistence. Deploy a deliberately bad image, show readiness protecting traffic, then rollback. Verify no secrets in evidence. Record exact image digests, cluster version, release SHA, commands and outputs.

An OpenShift manifest that has only been rendered must be labelled untested. Do not claim production OpenShift experience from a local kind deployment. A PostgreSQL backup replica, Redis Sentinel or HPA must not appear as an implemented capability unless provisioned and tested. Include their production design and trade-offs in the HLD where appropriate.

## 9. P5 — evaluation and performance gates

Run all original cases, required eight and additional three, with actual outputs saved. Repetition target: at least three runs of each mandatory case, reporting every failure. Reserve one held-out set with at least eight new questions covering the same behaviors; report it separately from tuned cases. Temperature zero does not guarantee determinism.

| Scenario | Observable acceptance |
|---|---|
| Simple lookup | Correct fact, correct page, no unnecessary clarification |
| Cross-document A | Every subquestion covered using at least two documents |
| Cross-document B | Second distinct question, each claim supported |
| Ambiguity | Targeted clarification, original context retained on reply |
| Missing evidence | Explicit abstention; no fabricated number, claim or citation |
| Conflict | Both passages cited; precedence explained only if evidenced |
| Injection | Injected instructions ignored; no access/tool escalation |
| Timeout | Bounded actual attempts; recovery or useful partial within deadline |
| Adaptive retrieval | Trace shows result-driven action change and new supporting evidence |
| Follow-up | Entity/pronoun resolution grounded in fresh source evidence |

Keep the retrieve-once baseline on the same model, corpus, retrieval settings and applicable questions. Report excluded clarification/retry comparisons explicitly; do not claim overall superiority from incomparable denominators. If metadata retrieval is improved for both systems, apply it consistently and explain any capability differences.

Record per case: expected/actual answer and behavior, source/page, pass/fail, stop reason, logical tool calls, actual attempts/retries, model requests, tokens, latency, estimated cost and failure note. Report all-case and shared-case scores separately, plus required-case success rate, repeat variability and p50/p95 latency where sample size supports it.

Manual citation review must check that a passage supports the associated claim, not just that the quote appears on the page. Review conflicts, abstentions and injection examples explicitly. A second model can assist grading, but its agreement is not ground truth; preserve human adjudication and evidence.

Reduce avoidable overhead: inspect duplicate context, whole-page repetition and unnecessary planning calls. Preserve coverage and safety. Any token/latency improvement must be measured on the same questions and reported alongside correctness, rather than setting an arbitrary speed target.

Accessibility: keyboard-only login/upload/question/clarification/citation flow, focus restoration, labelled controls, loading/error announcements, contrast and mobile layout. Verify reconnecting SSE, expired auth, upload rejection and empty state. Preserve the current design and allow side panels to collapse where useful.

Release gate: all eight mandatory behaviors must have passing demonstrations, all failures must remain visible in the report, and no repeat may fabricate unsupported facts. If failures persist, document them plainly and prioritize core correctness over additional expansion. A passing demo is not a reliability percentage.

## 10. P6 — docs, demo and handoff

- Refresh `requirements.md`, `submission-checklist.md`, `evaluation.md`, `reproducibility.md`, runbook, summary and UI evaluation figures from the same release. Retire or explicitly date the stale `completeness-audit.md`.
- Correct chunk overlap to the actual configured value, currently 30; describe 10 synthetic policies plus 4 references consistently. Reference runs must identify SHA, corpus hashes, prompt/model/embedding and environment.
- Update HLD: authentication/ACL boundary, API, durable worker/job state, ingestion, object storage/PVCs, PostgreSQL/pgvector, Redis roles/fallback, OIDC issuer, agent decisions, tools, citation verification, stopping and failure paths. Label implemented deployment versus future scale design.
- Explain institutional policy versus reference guidance, cache-key/invalidation behavior, semester/version retention, backup/restore and what happens when Redis/database/model provider fails. Archive rules are an explicit product policy, not an assumption that every semester automatically deletes data.
- Add one ADR each for auth and Kubernetes, and update prior single-VM/state/Redis decisions with the new boundaries. Explain why a single bounded agent and modular application are sufficient.
- Demonstrate login, two-user isolation, multi-document answer, natural re-retrieval, clarification/follow-up, conflict, timeout and citations. Keep a recorded/reproducible backup path if live provider or network fails. Label prerecorded or fake-model demonstrations accurately.
- Prepare a 20-minute take-home walkthrough and separate 30-minute HLD drill. Practice the data flow, one hard trade-off, one failure and recovery, measured agent-vs-baseline costs, and a small code modification.
- Complete release checks on a clean checkout; CI tests/image builds must actually run. Record Compose and Kubernetes evidence on the submitted release, not an earlier commit. Tag the release and verify reviewer access and deployed URL.
- Assemble repo/setup, reproducibility notes, architecture diagram, evaluation outputs/traces, walkthrough/video, achievement/limitations summary and deployment runbook. Do not send email automatically; Om reviews and sends the submission.

## 11. Suggested execution schedule

Effort is an estimate, not a promise. Auth, job recovery and orchestration may take longer than expected; reserve integration time rather than spending all available hours adding features.

| Window | Work and checkpoint |
|---|---|
| Thursday night | Baseline/trace confirmation; agree contracts and freeze scope; assign P1/P2/P3 owners |
| Friday morning | Agent repairs and auth implementation; durable job/storage implementation; unit and integration tests |
| Friday afternoon | Integrate ownership/jobs/storage; Compose end-to-end; begin Kubernetes with the integrated images |
| Friday evening | Working login + required-case improvements + local cluster boot. If any is blocked, concentrate implementers there |
| Saturday morning | Kubernetes drills, isolation/outage/restart fixes, held-out and repeated real-model evaluation |
| Saturday afternoon | Freeze features; manual citations, docs/HLD/presentation, clean-checkout and deployment verification |
| Saturday evening | Record demo, full mock, release candidate and final checklist |
| Sunday 9:00–10:30 AM | Final smoke and artifact/access check; Om submits ahead of noon; retain contingency buffer |

If time contracts, reduce infrastructure breadth to a tested single-replica Kubernetes deployment with explicit limitations; retain authentication, Compose, the eight demonstrations and truthful evidence. Do not trade a working required stack for untested manifests or claim HA that has not been built.

## 12. Copyable implementation instruction

> Read `docs/remaining-execution-plan.md`, the assignment PDF and current source. Implement only your assigned work package. Confirm the baseline and current status before edits. Preserve existing UI, corpus, real-model results and the required Docker Compose path. Agree shared schema/migration changes with the integrator. Add focused tests, run relevant checks, and produce a handoff with changed files, commands/results, commit SHA, unresolved risks and the next dependency. Do not hardcode evaluation answers, weaken substantive checks, invent results, expose credentials, claim untested deployment features, or send any email. Document any deviation from this plan and its reason.

## 13. Technical references

Use pinned dependency versions selected at implementation time and verify them against official documentation.

- Kubernetes Deployments: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- Kubernetes StatefulSets: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
- Persistent volumes/access modes: https://kubernetes.io/docs/concepts/storage/persistent-volumes/
- HPA/Metrics Server prerequisites: https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/
- Pod Security Standards: https://kubernetes.io/docs/concepts/security/pod-security-standards/
- Keycloak OIDC endpoints: https://www.keycloak.org/securing-apps/oidc-layers
- OAuth security best current practice: https://www.rfc-editor.org/rfc/rfc9700

## 14. Handoff log

Append entries; never replace earlier measurements.

| Date | Package | Implementer | Commit | Tests/evidence | Remaining |
|---|---|---|---|---|---|
| 2026-10-29 | Plan | ChatGPT | Baseline 0bc1d99 | Assignment/code/evaluation review | All work above is proposed; implementation not started by this plan |
