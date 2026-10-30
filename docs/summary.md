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

On three repeats of the 11 tuned cases the agent passed 24 of 33 case-runs and the one-pass baseline 15 of 27; six of the eight required scenarios pass every time (simple lookup, two multi-document cases, missing evidence, prompt injection, tool failure). On 10 held-out questions the agent passed 12 of 20 and the baseline 10 of 18, which is the better estimate of how it generalizes. The agent costs about ten times the tokens and takes about three and a half times as long; it earns it on cross-document, follow-up and vocabulary-mismatch questions and not on direct lookups. Every number and term in the claims of the last run was found on its cited page (a manual review by the assistant; please spot-check).

## Unfinished

- **One required behavior is still unreliable:** asking a clarifying question instead of answering for every variant. CASE-4 passed 0 of 3 repeats (and failed again after the last fix: the judge model called "How do I renew my account?" unambiguous); on the fresh set both genuinely ambiguous questions were asked about in all four runs and no specific question triggered a needless question in ten runs. Stating that a newer policy replaced an older one (CASE-6) now passes 3 of 3 after the metadata-driven template. The historical question (HELD-12) is answered correctly but without writing the year. Vocabulary bridging (CASE-9) still fails; the evidence-driven re-search for it was not built.
- **The verifier checks each claim, not every sentence of the prose.** Extra sentences were true in the cases I checked by hand, but nothing enforces it.
- **No public deployment, no recorded demo, and the work is still on `integration/full-stack`, not `main`.** Those are yours to do. CI has run on GitHub for this branch and passed all seven jobs ([run](https://github.com/theomthakur/policypilot/actions/runs/41068139547)).
- **Kubernetes limits:** one kind node (the S3-backed two-replica overlay was never run across nodes), one PostgreSQL pod (no replication), no autoscaler or load test, and the OpenShift overlay was only rendered. NetworkPolicies were enforced and checked on Calico, not on kind's default CNI.
- **Measured after the last fixes (30 Oct, one run per set):** tuned cases 8 of 11 (9 of 11 under the corrected CASE-4 check), fresh set 9 of 9, older held-out set 5 of 10. CASE-4 now asks first. HELD-4 is still not asked about, CASE-11 reaches the call limit with a correct answer, and CASE-9 is unstable. The fresh set guided the fixes, so it is no longer clean.
- **Sign-in** was tested against Keycloak only. There are no roles, no single logout, and rate limits are per client address.
- Small evaluation, one model, no load testing.

## With more time

1. Merge through pull requests, run CI on GitHub, tag a release, deploy behind HTTPS with a capped key and a real identity provider, and record the demo from the deployed release.
2. Make clarification dependable: a stronger model for the one-off ambiguity check, or a few-shot set drawn from held-out data, then measure on fresh questions (the current check is evidence-backed but misses and over-asks).
3. Evidence-driven re-retrieval and query expansion from the documents' own vocabulary (CASE-9), measured on the held-out set.
4. Verify every sentence of an answer, not only its claims.
5. Run the scaled overlay across real nodes with a load test and an autoscaler; managed PostgreSQL with replication; try the OpenShift overlay.
6. Roles, single logout and per-user rate limits; tracing and cost dashboards.
