#!/bin/sh
# Runs the final evaluation on the running local stack: the 11 tuned cases three times, and each of the two
# other question sets twice. Results go to eval/results/<prefix>-*. Usage: scripts/run_final_evaluation.sh r31 /path/to/python
set -eu
cd "$(dirname "$0")/.."
PREFIX="${1:?result prefix, e.g. r31}"
PY="${2:-python3}"
BASE="${POLICYPILOT_BASE_URL:-http://localhost:8080/api/v1}"
POLICYPILOT_DEMO_PASSCODE="${POLICYPILOT_DEMO_PASSCODE:-$(grep '^DEMO_PASSCODE=' .env | cut -d= -f2-)}"
export POLICYPILOT_DEMO_PASSCODE

for n in 1 2 3; do
  "$PY" eval/run.py --base-url "$BASE" --output-dir "eval/results/$PREFIX-tuned-$n" > "/tmp/$PREFIX-tuned-$n.log" 2>&1 || true
done
for n in 1 2; do
  "$PY" eval/run.py --base-url "$BASE" --cases eval/heldout2.yaml --output-dir "eval/results/$PREFIX-heldout2-$n" > "/tmp/$PREFIX-heldout2-$n.log" 2>&1 || true
done
for n in 1 2; do
  "$PY" eval/run.py --base-url "$BASE" --cases eval/heldout.yaml --output-dir "eval/results/$PREFIX-heldout-$n" > "/tmp/$PREFIX-heldout-$n.log" 2>&1 || true
done
echo finished > "/tmp/$PREFIX.done"
