# How AI assistance was used

The brief allows AI coding tools as long as the author can explain the implementation, justify the technical decisions, and show a clear understanding of the code. This page says exactly how they were used, what the author decided, what was rejected, and how every change was checked.

## Tools

- **Claude Code** (Anthropic's coding agent, in the terminal) did most of the implementation, running tests, builds and evaluations in this repository.
- **Other assistants (ChatGPT, Codex, Kiro, and a second Claude session)** were used only as independent reviewers. They read the repository and wrote audits and suggestions. They were not trusted: every claim was checked against the code before anything changed.

The raw session logs are not included. The same sessions also held unrelated personal material, so a short, honest account like this one replaces them.

## Who decided what

The author (Om Thakur) set the scope and made the judgment calls:

- the problem framing and the corpus (ten synthetic university IT policies plus four real NIST documents),
- a hand-written agent loop instead of a framework, so every decision is visible and easy to change live,
- the rule that **retrieved text is untrusted data** and the tools are read-only,
- the rule that **citations are verified in code** and an unsupported answer becomes "I could not find this",
- measuring choices instead of assuming them (chunk size, embeddings, a re-ranker),
- reporting results honestly, including that no question set is blind any more,
- cutting scope: no public deployment, and OpenShift left as written-but-not-run.

The assistant proposed designs and wrote most of the code. The author reviewed each design record (`docs/adr/`), directed changes, and decided what to keep.

## Process

1. **Design first.** Requirements got IDs (`docs/requirements.md`), and each significant choice got a short decision record with the alternatives considered (`docs/adr/`).
2. **Tests with every behaviour.** A bug fix starts with a failing test. The suite has 174 backend tests (run against real PostgreSQL and Redis in CI, where skipped tests fail the build) and 23 frontend tests.
3. **Measure, don't guess.** An evaluation harness (`eval/`) runs 11 required cases plus two further question sets against a one-pass baseline. Retrieval settings were chosen with a separate benchmark (`eval/retrieval_bench.py`).
4. **Real-model checks.** Behaviour changes were run with the real model, not only with scripted fakes, and kept only if they helped without making other sets worse.
5. **Browser checks.** UI changes were exercised in a headless browser (screenshots and scripted clicks), not just compiled.

## Suggestions that were rejected or reverted

This is the part that shows judgment more than the code does.

| Suggestion | What happened |
|---|---|
| Show answers as raw quoted page spans only (from an outside review branch) | Rejected. It broke the conflict-policy tests, dropped words like "2023" that the answer needs, and made answers read as quote fragments. |
| A multi-term ranking signal for one held-out question | Tried, improved the one-pass baseline but not the agent, so it was reverted. |
| Stop searching early when the token or call budget runs low | Tried on all question sets. It did not fix the target questions and one set got slightly worse, so it was discarded. |
| A "stop once answered" line in the agent's prompt | Tried on all sets with repeats. It did not fix the target and the results were noisy, so it was discarded. |
| A cross-encoder re-ranker, a larger embedding model, adding titles to chunks | Measured, no gain, not adopted (`docs/adr/0005`). |
| Public deployment and a real OpenShift run | Left out on purpose. The brief's requirement is a working Docker Compose deployment with evidence. |

## Mistakes the assistant made, and how they were caught

- A larger judge window pushed one case over its per-turn token limit. A re-run exposed it, and the judge's tokens no longer count against the agent's budget.
- A rule that decided whether the user had already named an option treated a word shared by only some options as naming one. A reviewer's trace reading found it, and a test now covers it.
- An outside review described files and tests that do not exist. It was checked against the repository and the invented parts were set aside.
- Several outside findings were real (a spoofable rate-limit address, a daily budget that could undercount after a Redis key loss, whole-number matching for figures, a summary that could survive an abstention). Each was reproduced first, then fixed with a test.

## What the author should be able to explain

Everything in `docs/system-design.md`, the architecture page in the app, and the decision records: how a document is chunked and indexed, how the agent decides its next action, how a citation is verified, what each guardrail does, what happens when a tool, the model, Redis or a worker fails, and what is still not solved (`docs/evaluation.md`, `docs/summary.md`).
