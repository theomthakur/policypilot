# Evaluation

## Status

The 11-case dataset and API-only runner are implemented and contract-validated. Final agent/baseline numbers remain **pending** until WS1's complete ingestion, retrieval, agent, and baseline API is integrated. No results are fabricated in this document.

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

## Required final comparison

Replace “pending” only from a committed evaluator output.

| Metric | Adaptive agent | Baseline |
|---|---:|---:|
| Correctness | pending | pending |
| Citation support | pending | pending |
| Task completion | pending | pending |
| Mean tool calls | pending | pending |
| Mean latency | pending | pending |
| Total tokens | pending | pending |
| Estimated cost | pending | pending |

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
