# Evaluation

## Status

The 11 frozen cases were run against the integrated stack with a real model (`openai/gpt-4o-mini` through OpenRouter, temperature 0, seed 42). The reference run is `eval/results/run-2026-10-29-gpt-4o-mini-r9/`, made with the final code (prompt v7) on the final 14-document library: the ten synthetic policies in their final layout plus four real NIST documents. Results are deterministic-check results only; the manual page review below is **not done yet**.

**Read this as a development measurement.** The system prompt and the citation-snapping rule were tuned against these same 11 cases (see the run history), and a model at temperature 0 still varies between runs: the last comparable agent runs passed 7, 6, 7 and 6 cases. A held-out set of new questions is the honest next test.

> **Note on page numbers and corpus.** Runs r1 to r8 used the original ten-document corpus in its first, plain layout. Before run r9 the synthetic PDFs were regenerated with a more realistic layout (banner, real tables, headers), which moved some pages, and four real NIST documents were added. The frozen-case table below and `eval/cases.yaml` use the new pages; run r9 is the only run on the final corpus.

## Method

Each case declares user turns, expected behavior, expected PDF pages, required/forbidden text, observable agent behavior, tool limits, and baseline applicability in `eval/cases.yaml`.

The runner:

1. Validates every case against `contracts/eval-case.schema.json` and every expected page against `corpus/manifest.json`.
2. Creates a new isolated API session for each case/system.
3. Runs the adaptive agent and the fixed retrieve-once baseline with the same corpus and model.
4. Polls the public turn endpoint and records the answer, trace, stop reason, tool calls, revisions, retries, latency, tokens, and estimated cost.
5. Fetches each cited page and checks that the normalized supporting quote occurs on that page.
6. Produces raw JSON, a Markdown comparison, and sanitized representative traces.
7. Reports failed checks and runtime errors instead of discarding unsuccessful runs.

Deterministic string/regex checks are transparent and repeatable but incomplete. They do not prove factual entailment or overall answer quality. The manual page log below is mandatory.

## Frozen cases

| Case | Behavior | Expected source pages | Baseline |
|---|---|---|---|
| CASE-1 | Simple guest-network lookup | Acceptable Use, p. 3 | Applicable |
| CASE-2 | Classification plus AI-use synthesis | Data Classification, p. 5; GenAI Guidance, p. 3 | Applicable |
| CASE-3 | Breach deadline plus VPN exception approver | Incident Response, p. 2; Remote Work, p. 4 | Applicable |
| CASE-4 | Account-type clarification and follow-up | Account Lifecycle, p. 4 | N/A: no clarification state |
| CASE-5 | Absent home-internet reimbursement | No source | Applicable |
| CASE-6 | 2023/2025 password conflict | Password Policy, p. 2; Identity Standard, p. 4 | Applicable |
| CASE-7 | Prompt injection inside an HPC policy | Research Computing, p. 5; injection is on p. 8 | Applicable |
| CASE-8 | Deterministic first-search timeout | Cloud Services, p. 3 | N/A: no retry policy |
| CASE-9 | Weak wording followed by revised retrieval | Data Classification, p. 8; Cloud Services, p. 1 | Applicable |
| CASE-10 | Multi-part, one document | Incident Response, pp. 2 and 3 | Applicable |
| CASE-11 | Pronoun-resolving follow-up | Incident Response, p. 3 | Applicable |

## Final comparison (run r9, 14-document library)

The baseline is not applicable to CASE-4 (clarification) and CASE-8 (retry), so it covers 9 cases. The agent column is shown for all 11 cases and, in brackets, for the same 9 cases as the baseline.

| Metric | Adaptive agent | Baseline |
|---|---:|---:|
| Cases passed (all deterministic checks) | 6 of 11 (5 of 9) | 4 of 9 |
| Correctness (mean of fact and behavior checks) | 0.87 (0.88) | 0.65 |
| Citation support (quote literally on the cited page) | 16 of 16 | 10 of 10 |
| Task completion (mean) | 0.87 (0.87) | 0.73 |
| Mean tool calls | 3.9 | 1.1 |
| Mean latency | 7.9 s | 2.4 s |
| Tokens (prompt + completion), all cases | 238,580 | 21,350 |
| Estimated cost, all cases | $0.038 | $0.004 |

Per case (agent, baseline): CASE-1 pass, pass. CASE-2 pass, pass. CASE-3 pass, fail. CASE-4 fail, n/a. CASE-5 fail, fail. CASE-6 fail, fail. CASE-7 pass, pass. CASE-8 pass, n/a. CASE-9 fail, fail. CASE-10 pass, pass. CASE-11 fail, fail.

**What this shows.** On the final library the agent is ahead on the 9 shared cases (5 passes to 4, correctness 0.88 against 0.65) at about eleven times the tokens and three times the latency. The earlier run on the original ten documents had them close (6 to 5, correctness 0.89 against 0.82); adding four long, real documents with overlapping vocabulary hurt the single-pass baseline more, because one search is easier to mislead when more of the library looks relevant. This is one run per setting, so treat the widening gap as a direction, not a result. Where the question is a direct lookup that one good search answers (CASE-1, 2, 7, 10), the baseline is as good and far cheaper. The agent also handles a timed-out tool (CASE-8) that the baseline cannot retry. Citation support is 100 percent for both because a citation that fails the literal-quote check is never shown.

## Manual citation check log

For each system/case, open the generated PDF and verify that the cited passage supports the exact claim, not merely that the quote exists.

| Case | System | Cited document/page checked | Claim supported | Reviewer | Note |
|---|---|---|---|---|---|
| CASE-1 | agent | pending | pending | | |
| CASE-1 | baseline | pending | pending | | |
| CASE-2 | agent | pending | pending | | |
| CASE-2 | baseline | pending | pending | | |
| CASE-3 | agent | pending | pending | | |
| CASE-3 | baseline | pending | pending | | |
| CASE-4 | agent | pending | pending | | Baseline excluded |
| CASE-5 | agent | no citation expected | pending | | |
| CASE-5 | baseline | no citation expected | pending | | |
| CASE-6 | agent | pending | pending | | Both dated sources required |
| CASE-6 | baseline | pending | pending | | Both dated sources required |
| CASE-7 | agent | pending | pending | | Confirm injected command was not followed |
| CASE-7 | baseline | pending | pending | | Confirm injected command was not followed |
| CASE-8 | agent | pending | pending | | Baseline excluded |
| CASE-9 | agent | pending | pending | | Confirm result-driven query revision in trace |
| CASE-9 | baseline | pending | pending | | |
| CASE-10 | agent | pending | pending | | |
| CASE-10 | baseline | pending | pending | | |
| CASE-11 | agent | pending | pending | | |
| CASE-11 | baseline | pending | pending | | |

## Failure analysis (run r9)

These causes come from the failed check names and the saved traces. They are not yet confirmed by a manual read of every trace.

- **CASE-4, agent.** The agent answered for every account type instead of asking which one applies, so no clarification was requested. Cause: agent planning. Prompt rules, an early clarification and a post-search checkpoint (run r6) were all tried; the model either never asks or asks on everything. The next step is a structured field the code acts on, not more prose.
- **CASE-5, agent and baseline.** The documents contain nothing about reimbursement. The agent's answer was right but it did not attach the expected missing-evidence notice; the baseline answered correctly in words the check's regular expression does not accept. Cause: model formatting for the agent; evaluator limit for the baseline.
- **CASE-6, agent and baseline.** Only the 2023 password policy was retrieved; the 2025 standard that supersedes it was never found. Cause: retrieval plus planning. The question's wording matches the old policy, and nothing in the first results hints that a newer standard exists.
- **CASE-9, agent and baseline.** The answer cited related pages, not the expected Data Classification and Approved Cloud Services pages. Cause: retrieval. The question uses everyday wording ("internet-hosted file repository") and the policy uses its own terms; neither system bridged the vocabulary. Similarity scores cannot flag this as weak evidence (see ADR 0005).
- **CASE-11, agent and baseline.** The follow-up needs the incident team lead's role and phone number from the synthetic plan. The agent used all its searches (10 tool calls) and missed the phone number; the baseline cannot resolve "her". The new NIST incident-response document competes with the synthetic plan for these questions, which is a likely cause of the agent's regression from the earlier runs.
- **CASE-3 flips between runs.** It passed for the agent in r9 and failed for the baseline; earlier it failed for the agent once. Treat it as unstable.

**Evaluator limits.** The checks are string and regular-expression checks. They can fail an answer that is correct in different words and pass one that is wrong but contains the right words. The manual log above is the real check.

## Failure analysis template

For every failure, record:

- Observed response and trace.
- Failed expected behavior or source.
- Whether the cause was retrieval, agent planning, answer composition, citation validation, tool/dependency failure, or evaluator limitation.
- Whether a retry changes the outcome.
- The smallest corrective change and its trade-off.
- Whether the same change harms another case or increases latency/cost.

At least one honest failure should remain in the final narrative if it reflects real model/system limitations.

## Interpreting agent overhead

Iteration is expected to help ambiguous, cross-document, conflict, and vocabulary-mismatch cases. It can add unnecessary tool calls, latency, and token cost to direct lookups. The final report must name cases where the baseline is equally correct or more efficient; agentic behavior is not assumed to win every comparison.
