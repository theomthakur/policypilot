# PolicyPilot evaluation

The evaluation runner calls only the public REST API. It compares the adaptive agent with the retrieve-once/generate-once baseline on the same corpus and configured model.

## Validate the dataset without an API

```sh
python -m venv .venv
.venv/bin/pip install -r eval/requirements.txt
.venv/bin/python eval/run.py --validate-only
```

## Run the evaluation

```sh
POLICYPILOT_BASE_URL=http://localhost:8000/api/v1 \
  .venv/bin/python eval/run.py
```

Set `POLICYPILOT_DEMO_PASSCODE` when the API gate is enabled. Use `--case CASE-1` for a focused run. Results are written beneath `eval/results/<UTC timestamp>/` unless `--output-dir` is supplied.

The runner checks deterministic facts and behavior. It does not claim that substring matching proves semantic correctness. Every cited page in the final report must also be checked manually and recorded in `docs/evaluation.md`.
