# Evaluation

## Status

The 11 frozen cases were run against the integrated stack with a real model (`openai/gpt-4o-mini` through OpenRouter, temperature 0, seed 42, prompt v3). The reference run is `eval/results/run-2026-10-29-gpt-4o-mini-r5/`. Results are deterministic-check results only; the manual page review below is **not done yet**.

**Read this as a development measurement.** The system prompt and the citation-snapping rule were tuned against these same 11 cases (see the run history). A held-out set of new questions would be the honest next test.

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

## Final comparison (run r5)

The baseline is not applicable to CASE-4 (clarification) and CASE-8 (retry), so it covers 9 cases. The agent column is shown for all 11 cases and, in brackets, for the same 9 cases as the baseline.

| Metric | Adaptive agent | Baseline |
|---|---:|---:|
| Cases passed (all deterministic checks) | 7 of 11 (6 of 9) | 6 of 9 |
| Correctness (mean of fact and behavior checks) | 0.86 (0.86) | 0.84 |
| Citation support (quote literally on the cited page) | 15 of 15 | 11 of 11 |
| Task completion (mean) | 0.90 (0.91) | 0.87 |
| Mean tool calls | 4.3 | 1.1 |
| Mean latency | 8.2 s | 2.7 s |
| Tokens (prompt + completion), all cases | 222,616 | 20,501 |
| Estimated cost, all cases | $0.036 | $0.004 |

Per case (agent, baseline): CASE-1 pass, pass. CASE-2 pass, pass. CASE-3 fail, pass. CASE-4 fail, n/a. CASE-5 pass, pass. CASE-6 fail, fail. CASE-7 pass, pass. CASE-8 pass, n/a. CASE-9 fail, fail. CASE-10 pass, pass. CASE-11 pass, fail.

**What this shows.** On the 9 shared cases the agent and the baseline are close on correctness; the agent costs about ten times as much and is three times slower. The agent wins where iteration is the point: the follow-up that needs the previous turn (CASE-11) and the timed-out tool (CASE-8, which the baseline cannot handle). The baseline wins CASE-3, where the extra searching did not help. Citation support is 100 percent for both because a citation that fails the literal-quote check is never shown.

## Run history (same corpus, same model, same 11 cases)

| Run | Change since the previous run | Agent passed | Baseline passed (of 9) |
|---|---|---:|---:|
| r1 | First real-model run | 0 of 11 | 2 |
| r2 | Citation quotes stored as the literal page span | 4 | 3 |
| r3 | Inexact quotes snap to the page sentence; search before answering; every follow-up search traced | 7 | 5 |
| r4 | Prompt v2: ask for clarification before searching (too eager, asked on most questions) | 4 | 6 |
| r5 | Prompt v3: clarify only after a first search; code rejects an early clarification | 7 | 6 |

r1 failed almost entirely because the model wrapped quotes in quotation marks, which the verifier accepted but the evaluator (correctly) did not. r4 is kept as evidence that a prompt change can make things worse.

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

## Failure analysis (run r5)

These causes come from the failed check names and the saved traces. They are not yet confirmed by a manual read of every trace.

- **CASE-3, agent (baseline passes).** Both documents were found and cited; the answer did not state the "one hour" reporting deadline in the form the check requires. Cause: answer composition. A retry may change it; the change would be a prompt rule to quote deadlines verbatim, with a risk of longer answers.
- **CASE-4, agent.** The agent searched, then answered for every account type instead of asking which one applies, and the follow-up turn then did not reach the sponsored-account rule. Cause: agent planning. The search-first clarification rule (v3) is not reliable with this model; a stronger model or a structured "needs clarification" field in the plan would be the next step.
- **CASE-6, agent and baseline.** Only the 2023 password policy was retrieved; the 2025 standard that supersedes it was never found. Cause: retrieval plus planning. The question's wording matches the old policy, and nothing in the first results hints that a newer standard exists. A "check for a newer version" step helped in some runs and cost tool calls in others.
- **CASE-9, agent and baseline.** The answer cited related pages, not the expected Data Classification and Approved Cloud Services pages. Cause: retrieval. The question uses everyday wording ("internet-hosted file repository") and the policy uses its own terms; neither system bridged the vocabulary. Similarity scores cannot flag this as weak evidence (see ADR 0005).
- **CASE-11, baseline.** A single retrieval cannot resolve "her" from the previous turn. This is the intended weakness of the baseline.

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
