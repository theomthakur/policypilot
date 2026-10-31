# Reliability evaluation and release plan

This document records the release procedure for the reliability work already
integrated into `integration/full-stack`. It contains no new score claims.

## Before the 2 PM Saturday code freeze

1. Diagnose HELD-2, HELD-7, HELD-8 and HELD-9 individually. Preserve the
   original trace, make the smallest isolated change, add a regression test,
   then record a before/after run. Revert a change that damages another
   critical behavior.
2. Re-run the frozen regression suites on the final candidate commit, with
   repeats for ambiguity, conflict, adaptive retrieval and follow-ups. These
   suites are diagnostic only because they have already informed development.
3. Run a separately written and frozen 20-question blind set three times.
   Do not tune against its results before the freeze. Record commit SHA, corpus
   manifest hash, model/provider, temperature, seed, price assumptions and UTC
   timestamps with every run.
4. Count provider failures, rate limits and budget stops as invalid runs, not
   product failures. Keep the raw output that explains each replacement run.
5. Update the canonical block in `docs/evaluation.md` only with measured,
   dated results from the frozen final commit. Report every repeat, category
   rates, median cost/latency, false-clarification rate and limit-stop rate.

## After the freeze

1. Run `scripts/verify_clean_checkout.sh` and confirm remote CI is green on
   the exact release commit.
2. Update `docs/demo.md` for the final local setup. Save demo traces and final
   answers as evidence, but do not represent a rehearsal as evaluation.
3. Generate the 20-citation spot-check sheet: claim, title/page, displayed
   literal span, reviewer result and notes for every row.
4. If agent-work provenance is included, commit only a redacted, reviewed
   export—not raw transcripts. Scan it for API keys, `.env` values, personal
   information, internal paths and copied third-party material before staging.
5. Restore the daily budget cap to `1.00`, run a secret scan, merge to `main`
   and tag the release only after all checks pass.

## Evidence boundary

The 11 tuned cases and the existing held-out files remain regression suites,
not blind generalization evidence. The release headline must come from the new
frozen 20-question set, while all earlier results remain in the evaluation
history for transparency.
