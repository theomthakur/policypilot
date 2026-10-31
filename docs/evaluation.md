# Evaluation

## Final evaluated release (read this first)

Everything below this block is the history of how the numbers were reached. This block is the current, canonical result.

Raw reports for the canonical run are in [`eval/results/r31-tuned-1/report.md`](../eval/results/r31-tuned-1/report.md), [`r31-tuned-2`](../eval/results/r31-tuned-2/report.md), [`r31-tuned-3`](../eval/results/r31-tuned-3/report.md), [`r31-heldout2-1`](../eval/results/r31-heldout2-1/report.md), [`r31-heldout2-2`](../eval/results/r31-heldout2-2/report.md), [`r31-heldout-1`](../eval/results/r31-heldout-1/report.md), and [`r31-heldout-2`](../eval/results/r31-heldout-2/report.md). When an older section differs, this block takes precedence.

- **Code:** branch `integration/full-stack`, evaluated at commit `f6981bc`. Every commit after the agent's last behaviour change (`4102de1`) is documentation or scripts only, so these runs describe the submitted agent.
- **Prompt version:** v10. **Agent model:** `openai/gpt-4o-mini`; **ambiguity judge:** `openai/gpt-4o`; temperature 0, seed 42; 14-document library, corpus manifest SHA-256 `e80b6f47...2a69` (`corpus/manifest.json`).
- **Date:** 31 Oct 2026 (US Eastern), runs `r31-*` in `eval/results/`. Commands: `scripts/run_final_evaluation.sh r31 <python>`.
- **Results.** The 11 tuned cases were run three times, and each of the other two sets twice:

| Set | Agent | One-pass baseline |
|---|---:|---:|
| 11 tuned cases, 3 runs (`eval/cases.yaml`) | **29 of 33** (10, 10, 9 of 11) | 15 of 27 |
| 9 newer questions, 2 runs (`eval/heldout2.yaml`) | **18 of 18** | 10 of 14 |
| 10 older held-out questions, 2 runs (`eval/heldout.yaml`) | **12 of 20** (6 and 6) | 12 of 18 |

- **Per case, tuned set (3 runs):** CASE-1, 2, 3, 4, 5, 6, 7, 8 and 10 passed 3 of 3. CASE-11 passed 2 of 3 (the third run reached the call limit). **CASE-9 failed 3 of 3**: in one run the agent asked a needless clarifying question, in one it answered with a missing fact, and in one it hit the call limit.
- **Where the agent helps and where it does not:** the agent beats the baseline on one of the two multi-document cases (CASE-3), the conflicting-sources case (CASE-6) and the follow-up (CASE-11), and it is the only system that can ask a clarifying question (CASE-4) or recover from a failed tool call (CASE-8). On direct lookups, the other multi-document case, missing evidence and injection (CASE-1, 2, 5, 7, 10) the baseline passes too, at a fraction of the cost. On the older held-out set the baseline scores about the same as the agent (12 of 18 against 12 of 20).
- **Cost and latency (tuned set):** the agent costs about $0.011 and takes a median 8.1 s per question; the baseline about $0.0005 and 1.8 s. The agent uses roughly ten times the tokens and twenty times the cost, because the ambiguity judge is a larger model.
- **Known failures:** CASE-9 (above); CASE-11 (one run in three); on the older set HELD-2, 7, 8 and 9 failed both runs.
- **Why the four older held-out questions fail (diagnosed from the saved traces).** HELD-2 ("When does an inactive Northfield account get suspended?") has several valid answers: the agent finds a real 90-day student rule, while the case expects the 180-day research-computing rule, so the question is arguably ambiguous and should have prompted a clarifying question. HELD-9 (a "temporary working disk") is answered from a competing, plausible rule (a 7-day transfer zone) instead of the scratch-storage rule that was also retrieved. HELD-7 retrieves both the 2023 and 2025 policies but answers only from the newer one and so misses the conflict. HELD-8 gives the correct, cited answer but keeps reading pages it no longer needs and ends at the token limit, so it is marked incomplete. Three attempts to fix them (a retrieval ranking change, an early stop when budget runs low, and a "stop once answered" prompt line) did not help and were discarded; the causes are in how the agent chooses between evidence, not in a single bug, so they are left as known limits.
- **No set is blind.** The 11 tuned cases were used to tune the system. The 9 newer questions were written before the changes, but their failures were then used to diagnose and fix behavior. The 10 older held-out questions have been looked at several times, and two of their labels were corrected after seeing results. Every number is a single run on a noisy model, so differences of one or two cases are not evidence of change. A fresh blind set of at least 20 questions was not run.
- **What the numbers do and do not show:** the citation check proves that each cited quote appears on the cited page. It does not prove that every sentence of an answer's prose is supported by that quote.

### Earlier runs

The sections that follow are historical experiments kept as a record. Where a number there differs from the table above, the table is current.

## Update, 30 October 2026 (runs r11 to r17 and the held-out set)

This section supersedes the headline numbers further down. The older sections (run r10, its failure analysis and citation log) are kept as the record of that run.

**What changed since r10.** Prompt v9; a structured ambiguity check after the first search; code that normalizes abstentions; document metadata (authority, version, effective date, documented supersession) with policy-family discovery and a conflict repair; follow-up search scoped to earlier sources; a 0.9 ranking weight for NIST reference material; truthful counters. Code and tests: see `docs/remaining-execution-plan.md` (handoff log). Same model (`openai/gpt-4o-mini`, temperature 0, seed 42), same 14-document library.

### Later the same day: fresh set, supersession template and facet gate (r18, `eval/heldout2.yaml`)

Outside LLM suggestions led to three changes, made after a second held-out set of nine new questions was written and committed (`eval/heldout2.yaml`, commit before the changes) and run against the old build:

1. **Supersession in code.** Documents' supersession metadata now carries scope terms and exception terms taken from what the 2025 standard says about itself. When a question is about a superseded provision in force today, both documents were read in the turn, and the question is not historical, the answer is *built from the two literal passages* (current rule, earlier rule, conflict notice) instead of trusting the model. Service accounts and other documented exceptions are left alone; historical questions are left alone; the earlier repair message obeys the same scope.
2. **A stricter clarification gate.** The judge model (`gpt-4o`, one short call per new question) must now fill `value_in_question`, `default_reading` and `answers_differ` and quote two passages from one document; code asks only if no value is named, there is no default, the answers differ and the quotes differ in a figure or most of their wording. A model that returns an unexpected field no longer silently disables the check (a bug found here: the skipped check is now visible in the trace).
3. **Summary figures are checked.** A sentence of the summary that states a figure no cited page contains is removed with a notice.

| Fresh set (9 questions) | Agent | Baseline |
|---|---:|---:|
| Before the changes (2 runs) | 7 of 18 | 10 of 14 |
| After the first version (2 runs; a field bug disabled the clarification check) | 11 of 18 | 10 of 14 |
| After the bug fix and the scope-aware repair (2 runs, `heldout2-after-c`, `-d`) | **14 of 18** | 10 of 14 |

After the fixes, per case (2 runs each): both ambiguous questions (HELD-15 backup policy, HELD-16 deleted files) **2 of 2**, and all four specific questions that must not trigger a question (HELD-14, 17, 18, 19) plus the service-account control (HELD-13, no supersession claimed) **2 of 2** with no needless clarification in 10 of 10 runs. The two conflict questions still failed: HELD-11 (current rule) 0 of 2, because the template picked a poor sentence from the 2025 standard; HELD-12 (historical) 0 of 2, because the answer was right but never wrote "2023".

I then made one more change, requiring the template's sentence to contain one of the documented scope terms, and re-ran only the conflict questions three times (`focus-heldout2-*`, `focus-case6-*`): **HELD-11 2 of 3** (baseline 0 of 3), HELD-12 still 0 of 3 (the literal "2023" is missing from the answer), and the tuned **CASE-6 3 of 3** (baseline 0 of 3), against 1 of 3 before. The fresh set was looked at while diagnosing, so these are no longer clean held-out numbers, and the HELD-11 fix was made after seeing its failure.

One tuned run after the bug fix (`run-2026-10-30-gpt-4o-mini-r19`): agent **9 of 11**, baseline 5 of 9. CASE-4 (ask which account) failed again: the judge model answered "not ambiguous" for it, with no default and no value named but `answers_differ` false. CASE-9 (cloud-services page not cited) also still fails. That one run is not a repeat set.

**Cost.** The ambiguity judge uses `gpt-4o`; the fresh-set agent runs averaged about $0.0072 per question against $0.0004 for the baseline (about eighteen times), median 6.7 s against 2.7 s.

**A deployment trap found here.** The application's own daily budget cap (`DAILY_BUDGET_USD`, default 1.00) stops all answers once reached, with a "budget used up" message; heavy evaluation hits it. For evaluation days raise it (the local `.env` is set to 8.00) or clear the Redis key `budget:<date>`. Two earlier sets of runs failed instantly for this reason and were deleted.

### Latest measurements (30 Oct evening, after the last two code changes; `r23-tuned`, `r24-tuned`, `r24-heldout2`, `r24-heldout`)

Two changes since the numbers below: the judge's answer is no longer thrown away when it lists more than five readings (it was, and the check was silently skipped), and the exact-words search the judge sees always runs and returns 10 results instead of 6. One run each, same model, new key:

| Set | Before the two changes (`r23-tuned`) | After (`r24-*`) | Baseline after |
|---|---:|---:|---:|
| 11 tuned cases | agent 8 of 11 | **agent 9 of 11** | 4 of 9 |
| 9 fresh cases (`heldout2.yaml`) | not run | **agent 9 of 9** | 5 of 7 |
| 10 held-out cases (`heldout.yaml`) | not run | **agent 5 of 10** | 5 of 9 |

What this shows, and what it does not:

- On the fresh set both ambiguous questions (HELD-15, HELD-16) passed for the first time and no specific question triggered a needless clarification. That set was used for diagnosis earlier, so it is not blind and is one run.
- On the tuned set CASE-4 (ask which account to renew) still fails: the clarification is not asked. CASE-11 failed in both runs by reaching the six-call limit while still giving a correct, cited answer. CASE-9 passed in r24 and failed in r23, so it is run-to-run variation.
- The older held-out set scored 5 of 10 in this single run (12 of 20 earlier). HELD-4 (ambiguous) is still not asked about; HELD-8, HELD-9 and HELD-2 failed. One run per set cannot separate a regression from noise, so treat these as indicative, not as a measured improvement.
- A judge probe on 15 questions asked on 3 of 6 ambiguous ones and on none of 9 specific ones.

### Naming-rule fix (`r26-tuned`, `r26-heldout2`, `r26-heldout`)

A reviewer's trace read found a bug: a word that appeared in some of the proposed readings (for example "storage" in "Project Storage" and "Scratch Storage", but not "Home Directories") counted as the user naming a reading, so "How much storage do I get?" never got its question. Only words unique to one reading now count, and the judge's "the user stated a value" flag follows the same rule. Test added; 156 backend tests pass.

One run per set, same model:

| Set | Agent | Baseline |
|---|---:|---:|
| 11 tuned cases | **9 of 11** | 4 of 9 |
| 9 fresh cases | **9 of 9** | 5 of 7 |
| 10 older held-out cases | **6 of 10** | 5 of 9 |

- HELD-4 (ambiguous) is asked for the first time and passes. CASE-4 asks and passes. No case that is not meant to be ambiguous received a clarifying question in any of the three runs.
- Still failing: CASE-11 (correct answer, reaches the six-call limit) and CASE-6 (a stop-reason failure this time; it passed in r23 to r25, so it is unstable). On the older set HELD-2, HELD-7, HELD-8 and HELD-9 fail; HELD-8 reached the call limit this time and passed in r25.
- The older held-out set has now been looked at several times, so it is no longer a clean test. Single runs cannot separate noise from change.

### Last change of 30 October (`r25-tuned`, `r25-heldout2`, `r25-heldout`)

Three more changes: the judge now sees up to 12 merged results (the merge used to keep 6 per search and 8 in all, so later chunks never reached it); the judge's "the user stated a value" flag only blocks a question when it points at what tells one reading from another (it blocked CASE-4 by saying "Northfield account"); and CASE-4's check changed.

**CASE-4 label correction, made after seeing its failures (so it is not a clean result).** The check required the answer to say "six months", which the user's own reply already says, and it failed in every run for that reason. It is now reported as a legacy fact and no longer decides pass or fail; the case requires "sponsor" and "14 business days". An outside suggestion to require "12 months|two consecutive" instead was tried and dropped, because the question does not ask for the renewal cap.

| Set | Agent | Baseline |
|---|---:|---:|
| 11 tuned cases | 8 of 11 as scored on the day (CASE-4 asked the question and gave the right steps; counted as 9 of 11 under the corrected check) | 5 of 9 |
| 9 fresh cases | 9 of 9 | 5 of 7 |
| 10 older held-out cases | 5 of 10 | 5 of 9 |

- The clarifying question for "How do I renew my Northfield account?" is asked for the first time. A judge probe asked on 3 of 6 ambiguous questions and on none of 9 specific ones.
- CASE-9 passed in r24 and failed in r25 (r23 failed too), so treat it as unstable. CASE-11 reaches the six-call limit with a correct answer, again.
- HELD-4 (ambiguous) is still not asked about, and HELD-2, HELD-7 and HELD-9 fail on the older set, as before. One run per set does not separate noise from regression.

### Final measurements (prompt v10, 31 Oct; `heldout2-v10b-g`, `-h`, `run-2026-10-31-gpt-4o-mini-r22`)

After the outside review (judge also sees the exact-words search, grounded defaults, failed quotes repaired from page text, a figure check on claims, common words out of the keyword search, the CASE-9 label corrected to page 2, and clarification decided from the judge's structured fields instead of its own "answerable" flag):

- **One run of the 11 tuned cases: agent 10 of 11, baseline 5 of 9.** Only CASE-4 (ask which account to renew) fails. CASE-9, CASE-11 and CASE-6 pass in this run.
- **Fresh set, two runs: agent 14 of 18, baseline 10 of 14.** The three conflict questions and the five specific or control questions all pass 2 of 2, with no needless clarification. The two ambiguous questions (HELD-15, HELD-16) still fail 0 of 2 each: HELD-15 now asks but the turn after the reply does not finish as "answered"; HELD-16 is not asked about.
- Mean cost about $0.009 per agent question (judge included) against $0.0004 for the baseline, median 6.7 s against 2.3 s.
- **Caveats.** The fresh set guided several fixes, so it is not clean. One tuned run is one sample; the earlier three-repeat table below was measured before these changes. Two earlier batches of runs were deleted because the application's daily spending cap stopped every turn (the cap reads the day's total from the database, so clearing Redis does not reset it).

### After an independent trace review (not yet measured)

A second model read the traces and code and found, among other things: the per-type renewal page never reached the judge because "Northfield" outranked it (the common-term filter measured the word's share over all chunks, not institutional ones); two code gates were skipped for short labels like "LMS account"; digits were ignored when checking whether the question names a kind; the offered question could list options the code had dropped; and after a clarification reply the agent re-read pages from scratch and hit its 6-call limit. Changes made in response (all covered by unit tests, **none re-run against the real model**):

- every proposed kind is logged in the trace with its quote, page and the reason it was dropped, so verdicts can be replayed;
- distinguishing tokens (digits and short acronyms included) decide whether the question already names a kind; a relevance gate requires at least two quoted rules to share a non-generic word with the question (a list of what exists does not); the offered question is built from, and only from, the verified options;
- the chosen option's page is read first on the reply turn (it counts toward the 6 calls and shows in the trace);
- the common-term filter measures over institutional chunks; the literal-question search is skipped when only stop words differ; a leaked near-copy of a test question was removed from the judge prompt;
- the evaluation runner marks a turn that ended in a provider error or a budget stop as **invalid** (never a failure) and aborts after three in a row.

Label corrections made after seeing results (so those two questions are no longer clean): HELD-2 (heldout.yaml) now expects the research-computing page 09 p3, the only inactivity rule in the corpus, instead of 08 p4, where "180 days" is the rehire rule; HELD-16's description now names the real contrast (Research Vault against the managed object stores' 90-day deleted-version rule), not the Transfer Zone. CASE-4's "six months" check is unchanged and is still failed in every run: the user's reply already says "six-month", so whether the answer must repeat it is an open decision.

**Why this is unmeasured.** Two evaluation keys each had a $1.00 limit and both were used up. All real-model runs after that point were deleted as invalid.

### Tuned cases, three repeats (r15, r16, r17; `eval/results/run-2026-10-30-gpt-4o-mini-r1{5,6,7}/`)

| Case | Category | Agent passed | Baseline passed | What fails |
|---|---|---:|---:|---|
| CASE-1 | simple lookup | 3/3 | 3/3 | |
| CASE-2 | multi-document | 3/3 | 3/3 | |
| CASE-3 | multi-document | 3/3 | 0/3 | baseline cites one document only |
| CASE-4 | ambiguity | **0/3** | n/a | see below |
| CASE-5 | missing evidence | 3/3 | 3/3 | |
| CASE-6 | conflict | **1/3** | 0/3 | see below |
| CASE-7 | injection | 3/3 | 3/3 | |
| CASE-8 | tool failure | 3/3 | n/a | |
| CASE-9 | adaptive retrieval | **0/3** | 0/3 | the cloud-services page is never cited |
| CASE-10 | one document, three parts | 3/3 | 3/3 | |
| CASE-11 | follow-up | 2/3 | 0/3 | one run searched the NIST incident document and ran out of searches |

Totals: agent **24 of 33** case-runs, baseline **15 of 27** (the baseline does not apply to CASE-4 and CASE-8). Median per case: agent 10.5 s, about 19,900 tokens, 4 tool calls, mean cost $0.0039; baseline 3.0 s, about 2,100 tokens, 1 tool call, $0.0004. The agent costs roughly ten times the tokens and takes about three and a half times as long, and it wins on cross-document and follow-up questions the one-pass baseline cannot do. Of the eight required scenarios, six pass in every repeat (1, 2, 3, 5, 7, 8) and two do not (4 and 6).

- **CASE-4 (ambiguity) fails every time, for a different reason than before.** The ambiguity check does fire and asks a question in some runs (r13 and r14 asked and then answered after the reply), but in r15 to r17 the check either judged the question answerable or the reply was answered without the six-month term the check requires. With real `gpt-4o-mini` this behavior is not reliable: a prompt-only check over-asked on almost everything (r11: 14 failures), and the quote-backed, head-noun-constrained version that stopped over-asking on the tuned cases misses this one.
- **CASE-6 (conflict).** When the answer cites both documents it carries a conflict notice generated from the documents' own supersession metadata. In two of three repeats the model still answered mainly from the 2023 policy, or exhausted its token budget (`limit_tokens` in r17) before stating the supersession in the words the check wants.
- **CASE-5 now passes**, using the broader abstention check (below).
- **Run-to-run variation is real** (CASE-6 and CASE-11 changed between identical runs), so one run proves little. Treat these as rates over three, not as guarantees.

### Held-out set (10 new questions, written before they were run; `eval/heldout.yaml`; runs h1 and h2)

Not used to tune anything. Two runs each:

| Case | Category | Agent | Baseline |
|---|---|---:|---:|
| HELD-1 | lookup | 2/2 | 2/2 |
| HELD-2 | lookup | 0/2 | 0/2 |
| HELD-3 | multi-document | 2/2 | 2/2 |
| HELD-4 | ambiguity | 0/2 | n/a |
| HELD-5 | missing evidence | 2/2 | 2/2 |
| HELD-6 | missing evidence | 1/2 | 2/2 |
| HELD-7 | conflict | 0/2 | 0/2 |
| HELD-8 | follow-up | 1/2 | 0/2 |
| HELD-9 | vocabulary mismatch | 2/2 | 0/2 |
| HELD-10 | lookup | 2/2 | 2/2 |

Agent **12 of 20**, baseline **10 of 18**. This is the number to quote for generalization, and it is lower than the tuned-case rate (60% against 73% for the agent). The failures are informative: HELD-2 and HELD-7 are specific questions where the agent still asked a clarifying question or missed the right document; HELD-4 is a genuinely ambiguous question that the agent did not ask about; HELD-6 once cited something while abstaining. On vocabulary mismatch (HELD-9, "temporary working disk" for scratch storage) the agent found the right page in both runs and the baseline in neither.

### Corrected abstention check (CASE-5, HELD-5, HELD-6)

The old check required a narrow phrase and failed r10's CASE-5 on wording even though the answer abstained. The new check keeps the structural requirements (stop reason `insufficient_evidence`, a `missing_evidence` notice, no citations, no invented amount) and uses a broad wording pattern. The old pattern is still computed and stored as `legacy_checks` in every result file but no longer decides pass or fail. Both agent and baseline are scored the same way. r10's CASE-5 failure is left as it was.

### Manual citation review (run r17, agent)

Done by the assistant that built the system, not by a human reviewer: **please spot-check.** For every claim in every answer I read the claim against the quote shown and then mechanically checked that every number and key term in the claim appears on the cited page (pdftotext of the source PDF).

- 21 of 21 claims on cited pages pass the mechanical check (no figure or term in a claim is absent from its cited page).
- Read by eye, the claims are supported, with two soft spots: CASE-4's "a faculty or staff sponsor" is supported by the page but not by the single quote shown; CASE-6's headline answer ("Yes, users are required to change passwords every 90 days") states the older rule first and the 2025 prohibition second, which is correct and cited but easy to misread.
- **What the verifier does not check:** it verifies each *claim's* quote against its page. Extra sentences in the answer's summary are not individually verified. In r17 the extra sentences I spot-checked (24-hour guest sessions, local copies of irreplaceable data, the 24/7 hotline, two consecutive renewal terms) were all in the documents, but that is luck of review, not a guarantee.
- The citation list shows one quote per page (the first claim's); a second claim on the same page is verified against its own quote but that quote is not displayed.

### Accessibility and keyboard checks

`scripts/e2e/a11y.mjs`: axe (WCAG 2.0/2.1 A and AA) found **0 violations** on the workspace, system design and presentation pages, in light and dark mode. A Tab walk found 38 stops, all named and on screen. The question box has no ring of its own; its container highlights on focus. The sign-in screen was not scanned with axe, and screen-reader behavior was not tested by hand.

### Counters

The totals now separate **logical tool calls** (the budget), **attempts** (retries and scope fallbacks included), **blocked calls**, **model requests** (the ambiguity check and repairs included) and tokens across all of them. The evaluator's `max_tool_calls` check still uses logical calls. Token and cost figures are provider-reported where the provider returns usage; a request that times out reports none, so cost is a slight underestimate on failed turns.

### Limits of this evaluation

Small (11 + 10 questions), one model, one corpus the team wrote, deterministic checks that cannot prove semantic correctness, and the tuned set was tuned on. Three repeats show variance but not a confidence interval.


## Status

The 11 frozen cases were run against the integrated stack with a real model (`openai/gpt-4o-mini` through OpenRouter, temperature 0, seed 42). The reference run is `eval/results/run-2026-10-29-gpt-4o-mini-r10/`, made with the final code (prompt v8) on the final 14-document library: the ten synthetic policies in their final layout plus four real NIST documents. Results are deterministic-check results only; the manual page review below is **not done yet**.

**Read this as a development measurement.** The system prompt and the citation-snapping rule were tuned against these same 11 cases (see the run history), and a model at temperature 0 still varies between runs: the last comparable agent runs passed 7, 6, 7, 6 and 6 cases. A held-out set of new questions is the honest next test.

> **Note on page numbers and corpus.** Runs r1 to r8 used the original ten-document corpus in its first, plain layout. Before run r9 the synthetic PDFs were regenerated with a more realistic layout (banner, real tables, headers), which moved some pages, and four real NIST documents were added. The frozen-case table below and `eval/cases.yaml` use the new pages; runs r9 and r10 are the runs on the final corpus.

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

## Final comparison (run r10, 14-document library)

The baseline is not applicable to CASE-4 (clarification) and CASE-8 (retry), so it covers 9 cases. The agent column is shown for all 11 cases and, in brackets, for the same 9 cases as the baseline. Run r9, on the same corpus with prompt v7, is listed beside it.

| Metric | Adaptive agent (r9 in brackets) | Baseline (r9 in brackets) |
|---|---:|---:|
| Cases passed (all deterministic checks) | 6 of 11 (6), 5 of 9 shared (5) | 5 of 9 (4) |
| Correctness (mean of fact and behavior checks) | 0.84 (0.87) | 0.68 (0.65) |
| Citation support (quote literally on the cited page) | 14 of 14 (16 of 16) | 9 of 9 (10 of 10) |
| Task completion (mean) | 0.87 (0.87) | 0.75 (0.73) |
| Mean tool calls | 4.0 (3.9) | 1.1 (1.1) |
| Mean latency | 7.8 s (7.9 s) | 2.7 s (2.4 s) |
| Tokens (prompt + completion), all cases | 233,002 (238,580) | 21,401 (21,350) |
| Estimated cost, all cases | $0.037 ($0.038) | $0.004 ($0.004) |

Per case (agent, baseline) in r10: CASE-1 pass, pass. CASE-2 pass, pass. CASE-3 pass, fail. CASE-4 fail, n/a. CASE-5 fail, pass. CASE-6 fail, fail. CASE-7 pass, pass. CASE-8 pass, n/a. CASE-9 fail, fail. CASE-10 pass, pass. CASE-11 fail, fail.

**What this shows.** The agent's average correctness is consistently higher than the baseline's across both runs on this library (0.84 to 0.87 against 0.65 to 0.68), but the number of cases passed outright is within noise: the agent passed 6 of 11 both times (5 of the 9 shared cases), the baseline 4 and then 5 of 9. The agent costs about eleven times the tokens and takes about three times as long. Where the question is a direct lookup that one good search answers (CASE-1, 2, 7, 10), the baseline is as good and far cheaper. The agent also handles a timed-out tool (CASE-8) that the baseline cannot retry. On the earlier ten-document corpus the two were closer on correctness (0.89 against 0.82, run r8); two runs on the larger library are not enough to say whether the gap widened. Citation support is 100 percent for both because a citation that fails the literal-quote check is never shown.

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

## Failure analysis (run r10)

These causes come from the failed check names and the saved traces. They are not yet confirmed by a manual read of every trace.

- **CASE-4, agent.** The agent answered for every account type instead of asking which one applies, so no clarification was requested. Cause: agent planning. Prompt rules, an early clarification and a post-search checkpoint (run r6) were all tried; the model either never asks or asks on everything. The next step is a structured field the code acts on, not more prose.
- **CASE-5, agent.** The documents contain nothing about reimbursement and the agent said so (stop reason correct), but its wording did not match the check's regular expression. In r9 the agent's answer lacked the missing-evidence notice instead; the baseline passed in r10 and failed in r9 on the same wording check. Cause: evaluator limit and model phrasing; the behavior is right and the check is strict.
- **CASE-6, agent and baseline.** Only the 2023 password policy was retrieved; the 2025 standard that supersedes it was never found. Cause: retrieval plus planning. The question's wording matches the old policy, and nothing in the first results hints that a newer standard exists. (In a later hand test the agent did answer "no, passwords do not expire" correctly from the newer standard, so this case is borderline.)
- **CASE-9, agent and baseline.** The answer cited related pages, not the expected Data Classification and Approved Cloud Services pages. Cause: retrieval. The question uses everyday wording ("internet-hosted file repository") and the policy uses its own terms; neither system bridged the vocabulary. Similarity scores cannot flag this as weak evidence (see ADR 0005).
- **CASE-11, agent and baseline.** The follow-up needs the incident team lead's role and phone number from the synthetic plan. The agent used all its searches (11 tool calls) and missed the contact details; the baseline cannot resolve "her". The new NIST incident-response document competes with the synthetic plan for these questions, which is a likely cause of the agent's regression from the earlier runs on the ten-document corpus.
- **CASE-3 flips between runs.** It passed for the agent in r9 and r10 and failed for the baseline in both; earlier it failed for the agent once. Treat it as unstable.

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
