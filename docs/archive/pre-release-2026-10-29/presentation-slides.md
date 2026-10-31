# PolicyPilot presentation plan

## Presentation principle

Lead with the user problem and a working flow, then explain the architecture through the behavior the audience just observed. Devpost's judging guidance emphasizes technological implementation, ease of use, demonstration, impact, idea quality, and design; its demo guidance recommends setting the scene briefly, showing the working project, and ending with the larger potential ([judging criteria](https://info.devpost.com/blog/understanding-hackathon-submission-and-judging-criteria), [demo guidance](https://info.devpost.com/blog/how-to-present-a-successful-hackathon-demo)).

The take-home interview provides 20 minutes for the assignment discussion and 30 minutes for system design. Use the first segment as a product-and-evidence narrative. Use the second to expand the high-level architecture under interviewer questions.

## 20-minute take-home walkthrough

### Slide 1 — The problem (1 minute)

**Title:** Policy answers are easy to generate and hard to trust.

**Show:** One policy question, several PDFs, and three failure risks: missed document, unsupported claim, incorrect page.

**Say:**

> PolicyPilot helps a user work across a small policy corpus. The goal is not merely a fluent answer. The goal is an answer whose retrieval decisions, limitations, and page evidence can be inspected.

### Slide 2 — What was built (1 minute)

**Show:** Browser screenshot with Documents, Conversation, and Activity; list the one-sentence definition of done.

**Say:**

> A user can upload a text PDF, ask a multi-part question, watch one bounded agent choose read-only tools, and open every verified page citation. The same stack runs through Docker Compose and is evaluated against a one-search baseline.

### Slide 3 — Live multi-document flow (3 minutes)

Use CASE-2. Skip login and setup.

1. Ask the classification/AI-use question.
2. Point to the plan and searches as they stream.
3. Show two documents in the evidence.
4. Open one citation and highlight the exact passage.
5. Point to latency, tokens, tool calls, and cost.

**Design cue:** Keep the answer in the primary canvas and open evidence beside it. This follows a useful interaction pattern found in ChatGPT Canvas and Claude Artifacts: preserve conversation context while giving the work product or source its own dedicated surface ([OpenAI Canvas](https://openai.com/index/introducing-canvas/), [Claude Projects and Artifacts](https://www.anthropic.com/news/projects)).

### Slide 4 — Why this is agentic (2 minutes)

Use CASE-9 or its saved trace.

**Show:** `weak tool result → query_revised → second tool action → verified answer`.

**Say:**

> A fixed RAG pipeline searches once and generates. Here, the first result leaves a sub-question uncovered. The model sees that structured observation and selects a revised query. The trace records what changed and the result-driven reason, without exposing private chain-of-thought.

### Slide 5 — High-level system design (3 minutes)

Open the in-app **System design** view or the first diagram in `docs/system-design.md`.

Explain left to right:

1. Browser and React workspace.
2. Caddy/nginx edge.
3. FastAPI contracts and SSE.
4. Bounded agent state machine and baseline.
5. Three read-only tools.
6. PostgreSQL/pgvector as source of truth.
7. Redis as replaceable acceleration/control.
8. Local embeddings and external chat model.
9. CI, evaluation, health, backup, and rollback around the runtime.

Do not read every label. Use one sentence per boundary and invite drill-down.

### Slide 6 — Grounding and safety (2 minutes)

**Show:** `claim → evidence ID → document/page → exact quote → citation chip`.

Cover:

- Page-bounded chunks.
- Corpus-only tools and argument validation.
- Retrieved text treated as untrusted.
- Prompt-injection test.
- Step/tool/retry/time/token limits.
- Partial or insufficient-evidence response.

**Say:**

> Exact quote presence proves provenance, not semantic entailment. That is why the evaluation also requires a manual claim-to-page review.

### Slide 7 — Persistence and failure behavior (1.5 minutes)

**Show:** PostgreSQL versus Redis responsibilities and the Redis outage result.

**Say:**

> Redis improves latency and coordination but holds no irreplaceable data. When it fails, readiness becomes degraded, sessions rebuild from PostgreSQL, retrieval runs uncached, and the user sees reduced performance rather than silent data loss.

### Slide 8 — Evaluation, including where the agent loses (2 minutes)

**Show:** The final agent/baseline table.

Cover:

- Same corpus, model, chunking, and retriever.
- Eight required plus three extra cases.
- Correctness, citation support, completion, tools, latency, tokens, cost.
- Baseline exclusions labeled N/A, not counted as agent wins.
- At least one genuine failure and the next corrective experiment.

### Slide 9 — Deployment and operations (1.5 minutes)

**Show:** One-VM deployment diagram and live health response.

Cover:

- Compose services and named volumes.
- Caddy TLS/security headers.
- Passcode, request limits, daily cap, capped provider key.
- Exact deploy, migration, smoke, persistence, Redis outage, update, and rollback drills.

### Slide 10 — Trade-offs and next step (1 minute)

Use four concise trade-offs:

- Explicit loop over agent framework.
- PostgreSQL/pgvector over separate vector DB.
- Local embeddings over hosted embeddings.
- One VM over Kubernetes.

End with the production path: SSO and corpus authorization, object storage, workers, managed data services, multiple stateless APIs, and centralized observability.

### Buffer (2 minutes)

Reserve time for a slow model call or one interviewer question. Keep saved traces and screenshots available if the live dependency is unavailable.

## 30-minute system-design discussion map

Let the interviewer choose depth. Start from the high-level diagram and branch by concern.

| If asked about… | Open this section | Core point |
|---|---|---|
| Agent behavior | State diagram | Results determine the next action; limits are part of state |
| Retrieval | Tool plane | Vector and lexical candidates are fused with RRF |
| Citations | Citation model | Evidence IDs and page quotes are verified server-side |
| Data | ER diagram | Provenance and traces are durable and relational |
| Redis | Redis table | Replaceable TTL state; PostgreSQL fallback |
| Safety | Trust-boundary diagram | Documents are data, tools are read-only, output is verified |
| Scale | Capacity table | Keep contracts while replacing single-node topology |
| Reliability | Failure-mode table | Every dependency has detection, user behavior, and recovery |
| Delivery | CI/CD gates | Fake-model smoke in CI, explicit paid evaluation outside CI |
| Deployment | VM diagram | Immutable tags, compatible migrations, smoke and rollback |

## Demo choreography

- Preload exact prompts in a plain text note.
- Start on the conversation screen, not the repository.
- Use one multi-document question and one short adaptive trace.
- Keep document upload, clarification, timeout, and Redis outage as prepared clips or saved evidence if live time is limited.
- Never wait silently. While a turn runs, explain the visible action event.
- Hide secrets, terminal history, personal browser tabs, and provider dashboards.
- End each demo path by opening the supporting page.

## Interface decisions informed by current AI products

PolicyPilot does not copy another product's visual identity. It borrows interaction principles that fit evidence-heavy work:

- **Dedicated work surface:** ChatGPT Canvas and Gemini Canvas separate a working artifact from ordinary chat, while keeping it in the same task context ([OpenAI](https://openai.com/index/introducing-canvas/), [Google](https://blog.google/products/gemini/gemini-collaboration-features/)). PolicyPilot applies that idea to an in-app system-design view and a citation page drawer.
- **Side-by-side context:** Claude Artifacts place generated work next to the conversation ([Anthropic](https://www.anthropic.com/news/projects)). PolicyPilot keeps the answer central and makes documents/activity adjacent rather than burying them in message text.
- **Source inspection:** Grok describes citations as a path for users to inspect and verify a source ([xAI](https://x.ai/blog/grok-1212)). PolicyPilot makes each source chip open the exact PDF page and supporting passage.
- **Project knowledge:** ChatGPT Projects and Claude Projects group files and conversations around a durable task ([OpenAI Projects](https://help.openai.com/en/articles/10169521-using-projects-in-chatgpt), [Claude Projects](https://www.anthropic.com/news/projects)). PolicyPilot presents the corpus as an explicit knowledge library and retains session context.
- **Progress without hidden reasoning:** The activity panel reports actions, statuses, summaries, and totals. It deliberately avoids simulated chain-of-thought.

Visual changes made for PolicyPilot:

- Replaced circular/bouncing logo treatments with a flat `P/` wordmark and a slim linear activity indicator.
- Bundled Plus Jakarta Sans and JetBrains Mono instead of relying on system fonts or remote font requests.
- Shifted from a dark green dashboard feel to a warm research-workspace palette with restrained teal and rust accents.
- Reduced rounded cards and decorative pills; used lines, page-like surfaces, and typographic hierarchy.
- Added a first-class System design view instead of treating architecture as an appendix.

## Likely questions and direct answers

### Why is this an agent rather than a RAG chain?

The LLM selects among multiple tools, receives structured observations, and may revise, clarify, inspect more pages, or stop. CASE-9 records a changed action caused by a weak result. The baseline performs one search and one generation.

### Why not LangGraph?

One agent and fewer than ten states do not need framework persistence or graph orchestration. The explicit loop is easier to bound, test, and explain. LangGraph becomes attractive if workflows branch across many agents, need resumable checkpoints, or involve human approvals.

### Does quote verification eliminate hallucination?

No. It blocks nonexistent provenance and unsupported displayed quotes. A quote can exist but fail to entail the claim. Manual evaluation and stronger entailment checks remain necessary.

### Why use Redis if PostgreSQL already exists?

Redis handles short-lived snapshots, caches, progress, rate counters, and budget counters. PostgreSQL owns durable state. The outage demonstration proves Redis improves operation without becoming a hidden hard dependency.

### Why one VM?

The required corpus and demo traffic fit one small host. A VM makes Compose, persistence, health, update, and rollback directly inspectable. The design documents how to move each stateful concern out when measured load or availability requires it.

## Source and licensing note

Content from the linked product and hackathon pages was summarized and rephrased. No interface text or visual design was copied. **Content was rephrased for compliance with licensing restrictions.**
