# Evaluation

## Status

The 11 frozen cases were run against the integrated stack with a real model (`openai/gpt-4o-mini` through OpenRouter, temperature 0, seed 42). The reference run is `eval/results/run-2026-10-29-gpt-4o-mini-r8/`, made with the final code (prompt v6). Results are deterministic-check results only; the manual page review below is **not done yet**.

**Read this as a development measurement.** The system prompt and the citation-snapping rule were tuned against these same 11 cases (see the run history), and a model at temperature 0 still varies between runs: the last three comparable runs passed 7, 6 and 7 cases for the agent. A held-out set of new questions is the honest next test.

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
| CASE-2 | Classification plus AI-use synthesis | Data Classification, p. 5; GenAI Guidance, p. 2 | Applicable |
| CASE-3 | Breach deadline plus VPN exception approver | Incident Response, p. 1; Remote Work, p. 4 | Applicable |
| CASE-4 | Account-type clarification and follow-up | Account Lifecycle, p. 3 | N/A: no clarification state |
| CASE-5 | Absent home-internet reimbursement | No source | Applicable |
| CASE-6 | 2023/2025 password conflict | Password Policy, p. 2; Identity Standard, p. 3 | Applicable |
| CASE-7 | Prompt injection inside an HPC policy | Research Computing, p. 5; injection is on p. 8 | Applicable |
| CASE-8 | Deterministic first-search timeout | Cloud Services, p. 3 | N/A: no retry policy |
| CASE-9 | Weak wording followed by revised retrieval | Data Classification, p. 7; Cloud Services, p. 1 | Applicable |
| CASE-10 | Multi-part, one document | Incident Response, pp. 1 and 3 | Applicable |
| CASE-11 | Pronoun-resolving follow-up | Incident Response, p. 3 | Applicable |

## Final comparison (run r8)

The baseline is not applicable to CASE-4 (clarification) and CASE-8 (retry), so it covers 9 cases. The agent column is shown for all 11 cases and, in brackets, for the same 9 cases as the baseline.

| Metric | Adaptive agent | Baseline |
|---|---:|---:|
| Cases passed (all deterministic checks) | 7 of 11 (6 of 9) | 5 of 9 |
| Correctness (mean of fact and behavior checks) | 0.88 (0.89) | 0.82 |
| Citation support (quote literally on the cited page) | 14 of 14 | 11 of 11 |
| Task completion (mean) | 0.88 (0.88) | 0.86 |
| Mean tool calls | 3.2 | 1.1 |
| Mean latency | 7.4 s | 2.7 s |
| Tokens (prompt + completion), all cases | 165,073 | 21,560 |
| Estimated cost, all cases | $0.027 | $0.004 |

Per case (agent, baseline): CASE-1 pass, pass. CASE-2 pass, pass. CASE-3 pass, pass. CASE-4 fail, n/a. CASE-5 fail, fail. CASE-6 fail, fail. CASE-7 pass, pass. CASE-8 pass, n/a. CASE-9 fail, fail. CASE-10 pass, pass. CASE-11 pass, fail.

**What this shows.** On the 9 shared cases the agent is slightly ahead (6 passes to 5) and a little more correct, at about eight times the tokens and three times the latency. The whole difference is CASE-11, the follow-up that needs the previous turn, which a single retrieval cannot resolve. Where the question is a direct lookup or a cross-document question that one good search answers (CASE-1, 2, 3, 7, 10), the baseline is as good and far cheaper. The agent also handles a timed-out tool (CASE-8) that the baseline has no way to retry. Citation support is 100 percent for both because a citation that fails the literal-quote check is never shown.

## Run history (same corpus, same model, same 11 cases)

| Run | Change since the previous run | Agent passed | Baseline passed (of 9) |
|---|---|---:|---:|
| r1 | First real-model run | 0 of 11 | 2 |
| r2 | Citation quotes stored as the literal page span | 4 | 3 |
| r3 | Inexact quotes snap to the page sentence; search before answering; every follow-up search traced | 7 | 5 |
| r4 | Prompt v2: ask for clarification before searching (too eager, asked on most questions) | 4 | 6 |
| r5 | Prompt v3: clarify only after a first search; code rejects an early clarification | 7 | 6 |
| r6 | Experiment: a one-time "do these passages differ by user type?" checkpoint after the first search | 0 | 5 |
| r7 | Checkpoint removed; conversational replies, failure fixes, prompt v5 | 6 | 5 |
| r8 | Prompt v6: meaningless input gets a polite "I did not understand" (final code) | 7 | 5 |

r1 failed almost entirely because the model wrapped quotes in quotation marks, which the verifier accepted but the evaluator (correctly) did not. r4 and r6 are kept as evidence that prompt and loop changes can make things much worse: both made the model ask for clarification on nearly every question. Runs r5, r7 and r8 differ by one case, mostly CASE-3 (answer wording) and CASE-5 (whether the model reports missing evidence or asks a question), which is ordinary run-to-run variation at this sample size.

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

## Failure analysis (run r8)

These causes come from the failed check names and the saved traces. They are not yet confirmed by a manual read of every trace.

- **CASE-4, agent.** The agent answered for every account type instead of asking which one applies, so no clarification was requested. Cause: agent planning. Prompt rules, an early clarification and a post-search checkpoint (run r6) were all tried; the model either never asks or asks on everything. The next step is a structured field the code acts on, not more prose.
- **CASE-5, agent and baseline.** The documents contain nothing about reimbursement. The baseline answered correctly in words the check's regular expression does not accept; the agent asked for the employee's role instead of reporting missing evidence. Cause: model behavior for the agent; evaluator limit for the baseline.
- **CASE-6, agent and baseline.** Only the 2023 password policy was retrieved; the 2025 standard that supersedes it was never found. Cause: retrieval plus planning. The question's wording matches the old policy, and nothing in the first results hints that a newer standard exists.
- **CASE-9, agent and baseline.** The answer cited related pages, not the expected Data Classification and Approved Cloud Services pages. Cause: retrieval. The question uses everyday wording ("internet-hosted file repository") and the policy uses its own terms; neither system bridged the vocabulary. Similarity scores cannot flag this as weak evidence (see ADR 0005).
- **CASE-11, baseline.** A single retrieval cannot resolve "her" from the previous turn. This is the intended weakness of the baseline.
- **CASE-3 flips between runs.** It failed in r7 on how the one-hour deadline was worded and passed in r5 and r8; treat it as unstable.

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
