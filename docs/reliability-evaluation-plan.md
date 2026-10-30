# Reliability evaluation plan

This plan evaluates the deterministic reliability changes on
`improve/reliability-and-evaluation`. It intentionally records a method, not
new scores: no live-model run should be represented as completed until the
OpenRouter key is available.

## What changed

| Risk | Product guardrail | Regression proof |
|---|---|---|
| A model lists two quoted policy variants but marks them as the same answer | The loop derives difference from the verified, relevant variants in one document; the model boolean remains trace telemetry | `test_evidence_backed_variants_override_a_false_difference_boolean` |
| A fluent summary says more than the cited quote proves | The verifier displays literal source spans as the claims and builds standard summaries only from those verified spans | `test_an_evidence_backed_summary_is_built_only_from_verified_claim_spans` |
| A follow-up burns its final data-tool slot after relevant evidence is already present | The loop blocks that redundant call and forces `final_answer` from the existing evidence | `test_focused_follow_up_reserves_the_final_search_slot_for_an_answer` |

## Fresh evaluation protocol

1. Write a **new 20-question set** in a private file before any model call.
   Include at least four ambiguous, four specific-control, four conflict or
   supersession, four insufficient-evidence, two injection or tool-failure,
   and two follow-up/adaptive-retrieval questions. Keep the exact questions and
   expected pages out of prompts and implementation.
2. Freeze the file with a commit and SHA-256. Only then copy it into `eval/` or
   give it to a reviewer to run. Do not change a label after a result; record a
   disputed label separately.
3. Run the adaptive agent and retrieve-once baseline with the same corpus,
   model, temperature, seed and provider pricing. Run each set **three times**:

   ```bash
   POLICYPILOT_BASE_URL=http://localhost:8080/api/v1 \
     python eval/run.py --cases eval/fresh-reliability.yaml \
     --output-dir eval/results/reliability-agent-r1
   ```

   Repeat with distinct output directories (`r2`, `r3`). Capture the active
   commit, `PROMPT_VERSION`, corpus manifest hash, model name, temperature,
   seed, provider, and date alongside every run.
4. Treat provider errors, rate limits and budget stops as **invalid**, not as
   failures. Re-run only the invalid turn and retain the raw result explaining
   why it was replaced.
5. Manually review every displayed claim in a random sample of at least ten
   answers. The check is simple: the displayed text must be a literal substring
   of its cited page, and the answer must not add an uncited factual sentence.

## Decision rules

- Report pass rate with numerator/denominator for each scenario category and
  each of the three repeats—never only the best run.
- Report false clarification rate on the specific-control questions separately
  from missed clarification rate on ambiguous questions.
- Report the fraction of answers ending at `limit_tool_calls`, especially for
  follow-ups, plus median tool calls, latency and model cost.
- Compare the branch only against the prior frozen build on the same fresh set.
  The existing `cases.yaml`, `heldout.yaml` and `heldout2.yaml` remain useful
  regression suites but are no longer blind.
- A change is worthwhile only if it improves or preserves grounded-answer pass
  rate **and** does not materially increase false clarifications, limit stops,
  median cost, or latency.

## Before merging or demoing

- [ ] `ruff`, `mypy`, backend unit tests, frontend lint/tests and a Docker
  smoke test pass.
- [ ] The Compose/API-level integration suite passes in an isolated test
  database; never point it at the running demo database because it truncates
  tables by design.
- [ ] Three fresh-set runs are stored under `eval/results/`.
- [ ] `docs/evaluation.md` is updated with the actual, dated measurements and
  explicit caveats; no projected figures are written as results.
