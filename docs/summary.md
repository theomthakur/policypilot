# Summary: what was built, what is unfinished, what would come next

## What was built

PolicyPilot is a full-stack agentic RAG application over 14 PDFs: ten synthetic university IT policies (85 pages; the generator and a manifest are in `corpus/`) and four real public NIST documents (146 pages) as a reference library. A user uploads PDFs or asks questions in a browser. A single tool-using agent plans, searches, searches again with different words, reads whole pages, asks a clarifying question or answers, and every citation is checked against the actual page text before it is shown.

- **Stack:** React and TypeScript behind nginx, FastAPI, PostgreSQL with pgvector, Redis, an OpenAI-compatible model client (OpenRouter), all started by Docker Compose. CI configuration is in `.github/workflows/ci.yml`.
- **Retrieval:** page-bounded 200-token chunks, vector plus full-text search fused with reciprocal rank fusion. These settings were chosen by a benchmark on the evaluation cases' expected pages (`eval/retrieval_bench.py`, ADR 0005); a reranker, a larger embedding model and a heading prefix were tested and not adopted.
- **Agent:** a hand-written bounded state machine with four read-only tools, step, tool, time and token limits, one retry, duplicate-call blocking, partial answers on limits, and untrusted treatment of retrieved text. Greetings, thanks and questions about the assistant get a direct reply, and a question nothing in the library is about is answered in code after one search.
- **Trust:** a claim is shown only if its quote is literal text on the cited page (provenance, location, then the exact span stored as the citation).
- **Operations:** optional OpenID Connect sign-in with per-user ownership of conversations and uploads, passcode, rate limit, daily budget cap, Redis-down fallback to PostgreSQL, readiness reporting, structured logs, and **durable jobs** (questions and uploads survive a crashed worker; shown by killing a worker mid-question on a real cluster).
- **Agent additions (30 Oct):** a quote-backed check that asks a clarifying question only when parallel kinds of a noun the user used are described in one document; document authority, version, effective date and documented supersession reaching retrieval and a conflict notice; follow-up search scoped to earlier sources; honest counters for logical calls, attempts, retries, blocked calls and model requests.
- **Evaluation:** an 11-case tuned suite (three repeats) plus a 10-question held-out set, run against the live API for the agent and a retrieve-once baseline; raw results are committed (`eval/results/`).
- **Deployment:** Docker Compose (required) and a Kubernetes path deployed and drilled on a local `kind` cluster (pod deletes, bad image with rollback, backup and restore, a crashed worker), with Keycloak sign-in through an ingress.
- **Interface:** workspace with a collapsible knowledge base and agent activity, a time-of-day greeting, a readable execution trace, a developer mode with metrics, sign-in screen and account menu, light and dark themes, an architecture page and a plain-language presentation.

## Results in one paragraph

On the final run (31 Oct 2026) the agent passed 29 of 33 runs of the 11 tuned cases (three runs) against 15 of 27 for the one-pass baseline, 18 of 18 on the newer questions (two runs) against 10 of 14, and 12 of 20 on the older held-out questions (two runs) against 12 of 18. Simple lookup, missing evidence, prompt injection, tool failure, clarification, conflicting sources and the multi-document cases passed every run; CASE-9 (a question that needs a rewritten search) failed all three, and the follow-up case failed once in three. The agent beats the baseline on one multi-document case, the conflict case and the follow-up, and ties it on direct lookups at a fraction of the cost. No set is blind any more and the samples are small, so small differences are noise. The agent costs about ten times the tokens and about four times the time. See the canonical block at the top of `docs/evaluation.md`. The citation check proves each quote is on its page; it does not check every sentence of the prose.

## Unfinished

- **Clarification is promising but not proven:** CASE-4 passed all three r31 tuned runs. The r31 result is still small and not blind, so it is evidence of behavior rather than a guarantee. CASE-6 also passed all three r31 tuned runs.
- **The verifier checks each claim, not every sentence of the prose.** It proves literal quotes appear on cited pages, but it does not prove full semantic support. The independent citation spot-check remains pending.
- **The reproducible walkthrough is complete.** The brief permits a recorded demo or a reproducible walkthrough, and `docs/demo.md` provides the latter. An independent 20-citation spot-check remains recommended. CI passed all seven jobs on the release candidate ([run](https://github.com/theomthakur/policypilot/actions/runs/41068139547)). A public deployment is an optional release step, not a claim made here.
- **Kubernetes limits:** one kind node (the S3-backed two-replica overlay was never run across nodes), one PostgreSQL pod (no replication), no autoscaler or load test, and the OpenShift overlay was only rendered. NetworkPolicies were enforced and checked on Calico, not on kind's default CNI.
- **Sign-in** was tested against Keycloak only. There are no roles, no single logout, and rate limits are per client address.
- Small evaluation, one model, no load testing.

## With more time

1. Merge through pull requests, run CI on GitHub, tag a release, deploy behind HTTPS with a capped key and a real identity provider, and record the demo from the deployed release.
2. Make clarification dependable: a stronger model for the one-off ambiguity check, or a few-shot set drawn from held-out data, then measure on fresh questions (the current check is evidence-backed but misses and over-asks).
3. Evidence-driven re-retrieval and query expansion from the documents' own vocabulary (CASE-9), measured on the held-out set.
4. Verify every sentence of an answer, not only its claims.
5. Run the scaled overlay across real nodes with a load test and an autoscaler; managed PostgreSQL with replication; try the OpenShift overlay.
6. Roles, single logout and per-user rate limits; tracing and cost dashboards.
