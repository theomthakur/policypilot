# PolicyPilot presentation and demo plan

This is the reviewer and interview walkthrough, not a marketing script. Target 18-20 minutes, leaving room for questions and a code modification.

## Presentation principle

**One screen proves the product; the HLD explains why it is trustworthy.** Do not add architecture slides or implementation claims inside the main application UI. Keep the live product focused on documents, answers, citations and the execution trace.

## Run of show

|        Time | Section               | What to show                                              | Main point                                                              |
| ----------: | --------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------- |
|   0:00-0:45 | Problem               | Title and one-sentence framing                            | Policy answers are useful only when a user can inspect the evidence.    |
|   0:45-1:30 | Scope and invariants  | Users, bounded corpus, session isolation, citations       | Groundedness and isolation are hard requirements.                       |
|   1:30-6:00 | Live product          | Multi-document case, trace and citation drawer            | This is working software, not a diagram.                                |
|   6:00-8:00 | Why an agent          | Weak result followed by a changed action                  | The loop adapts to evidence; it is not fixed retrieve-then-generate.    |
|  8:00-11:30 | HLD                   | One architecture diagram and query path                   | Explain service boundaries, state, tools and persistence.               |
| 11:30-13:30 | Trust and safety      | Citation checks, prompt injection and abstention          | Trust is enforced partly in code, not left to prompting.                |
| 13:30-16:00 | Evaluation            | Agent versus baseline table, latency/cost and one failure | Show measured trade-offs, not “agent always wins.”                      |
| 16:00-17:30 | Operations            | Compose, Redis outage, health and persistence             | The deployment has failure behavior, not just containers.               |
| 17:30-19:00 | Trade-offs and limits | Current/next table                                        | Be explicit about what is unfinished and when the architecture changes. |
| 19:00-20:00 | Close                 | Three outcomes and reviewer questions                     | Reproducible, inspectable and honest.                                   |

## Opening

> PolicyPilot is a policy research assistant that can search, inspect and combine evidence across a bounded PDF corpus. The key design decision is that it does not have to answer: it can retrieve again, ask a clarification, or stop when the evidence is insufficient. Every material answer claim is tied to a document page the user can open.

## Live demo sequence

### 1. Multi-document answer

Ask:

> A researcher has Level 3 confidential pre-publication data. What encryption is required at rest, and may the researcher paste it into a public consumer AI tool?

Show two source documents, verified citation chips, exact page text, tool count, latency and cost. Keep the explanation under 90 seconds.

### 2. Evidence-driven change of action

Ask:

> Where may I keep highly sensitive clinical study files in an internet-hosted file repository?

Show weak initial evidence, query revision/read action, and final cross-document evidence. Say explicitly what result caused the next action to change.

### 3. Clarification

Ask:

> How do I renew my Northfield account?

Reply that it is a sponsored guest account. Show that the original intent survives the clarification turn.

### 4. Controlled failure

Use the test-only CASE-8 path. Show one search timeout, one retry and either recovery or a bounded partial answer. Never enable arbitrary fault injection in the public demo.

## HLD drawing order

Draw or reveal one layer at a time:

1. Browser and same-origin gateway.
2. FastAPI authorization boundary.
3. Two paths: ingestion and query.
4. PostgreSQL/pgvector as durable truth; Redis as disposable acceleration.
5. Bounded agent state machine and three read-only tools.
6. Citation verifier before response.
7. Trace and metrics returning to the UI.

Do not begin with Kubernetes or hypothetical scale. Establish the actual workload and invariants first, then explain the scaling path.

## Evaluation story

The comparison must use the same corpus, retriever, model and output format.

- Baseline: one retrieval, one generation.
- Agent: may revise, read, clarify or recover within a larger declared budget.
- Report completion, citation precision/coverage, latency, tokens, cost and stop reason.
- Show at least one case where the baseline is faster and sufficient.
- Show at least one case where additional agent work improves task completion.
- Show a genuine failure and the resulting fix or remaining limitation.

Do not describe a tiny evaluation set as statistically significant.

## “What is real?” slide

Update this table at the final release commit.

| Capability            | Evidence required before saying it works      |
| --------------------- | --------------------------------------------- |
| Upload and indexing   | API integration test and successful UI upload |
| Agent adaptation      | Saved real-model trace with changed action    |
| Citation verification | Test plus page-level demo                     |
| Baseline comparison   | Raw results and aggregate report              |
| Redis fallback        | Outage script output                          |
| Persistence           | Restart script output and retained IDs        |
| Public deployment     | Signed-out smoke test against release SHA     |

Anything missing stays labelled planned or partial.

## Applied lessons from previous builds and hackathons

1. **Prove one thing clearly.** The main screen demonstrates answer, evidence and execution trace instead of presenting a feature wall.
2. **Diagram before code.** The HLD is a numbered story with a “production scale, not today” path.
3. **Show the evidence.** Citation drawer, action trace and evaluation artifacts are stronger than architectural claims.
4. **Rules belong in configuration.** Step limits, timeouts, retry count, model, thresholds and budget must be configurable and visible in reproducibility notes.
5. **Separate real from simulated.** Fake-model CI, test-only fault injection and real-model evaluation must be labelled distinctly.
6. **Design for the failure demo.** Redis outage, tool timeout, insufficient evidence and prompt injection each have an observable outcome.
7. **Human presentation beats generated polish.** Speak from bullet points; do not use an AI voiceover or exaggerated copy.
8. **One number per claim.** Use measured latency, token/cost, citation accuracy and case completion instead of adjectives.
9. **Record before the final feature.** Capture a working release demo before optional changes, then freeze functionality.
10. **Submit early and keep a fallback.** Verify every link signed out and keep a local Compose recording if hosting fails.

## Likely reviewer questions

### Why an agent instead of ordinary RAG?

Simple lookups do not need an agent. The agent earns its cost only for ambiguity, multi-document decomposition, weak initial evidence and bounded recovery. The baseline comparison measures that trade-off.

### Why PostgreSQL and pgvector?

At this corpus size, one transactional store simplifies authorization, metadata filters, text search, vector search, backup and Compose reproduction. Revisit the choice when measured chunk count or query load makes it the bottleneck.

### What does citation verification prove?

It proves that the cited evidence was retrieved in the turn, resolves to the stated document/page and contains the quoted support. It does not prove full semantic entailment, which is why the evaluation includes claim-level review.

### What happens when Redis fails?

Readiness reports degraded, sessions and turns remain durable in PostgreSQL, and retrieval runs uncached. Correctness remains available at higher latency.

### What would you change with another week?

Use a durable ingestion worker, add authenticated tenancy and ACLs, expand the held-out corpus/evaluation, measure reranking, and deploy managed data stores only if availability requirements justify them.

## Recording checklist

- Record against the final release SHA.
- Use a clean browser and pre-indexed corpus.
- Keep one HLD diagram, not several dense slides.
- Show exact sources and at least one adaptive trace.
- Show one honest failure or limitation.
- Hide secrets, passcodes, provider dashboards and private prompts.
- Keep a backup recording and a local Compose fallback.
- Add the final URL, release SHA and video link to the README.
