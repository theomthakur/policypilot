# Reproducibility

## Corpus

The repository includes ten fictional Northfield University Office of IT policy PDFs, their Markdown sources, and a deterministic generator.

```sh
python3 -m venv .venv
.venv/bin/pip install -r corpus/requirements.txt
.venv/bin/python corpus/generate.py
git diff --exit-code -- corpus
```

`corpus/manifest.json` records every title, version, effective date, PDF filename, page count, SHA-256 digest, evaluation case, and expected anchor page. ReportLab's invariant mode removes volatile PDF metadata. The generator verifies that every planted anchor can be extracted from its generated page.

The generated set contains 10 text-based PDFs and 74 pages. Every page says: “Synthetic document for a take-home assignment. Not an official NYU policy.”

## Models and prompts

The runtime configuration is versioned in `.env.example`:

- Chat client: OpenAI-compatible API.
- Planned evaluation chat model: `openai/gpt-4o-mini` through the configured provider.
- Embedding provider: local FastEmbed ONNX.
- Embedding model: `BAAI/bge-small-en-v1.5`.
- Embedding dimension: 384.
- Chat temperature: 0.
- Best-effort seed: 42.

Before the final run, verify provider availability and record the exact provider/model identifier and date in `eval/results/.../results.json`. Agent and baseline must use the same model, corpus, chunks, retriever, and temperature. Do not silently substitute a model between modes.

Prompts and their version identifiers live with the backend agent implementation. Tool schemas are canonical in `contracts/tools.schema.json`; answer and trace schemas are in `contracts/answer.schema.json` and `contracts/trace-event.schema.json`.

## Chunking and retrieval configuration

Defaults from `.env.example`:

- Page-bounded chunks: 200 tokens with a 30-token overlap (chosen by `eval/retrieval_bench.py`; see ADR 0005).
- Overlap: 50 tokens.
- Candidate count: 20 per retrieval method.
- Returned results: 6 by default.
- Reciprocal Rank Fusion constant: 60.
- Weak-result threshold: 0.02.

Every evaluation result must record effective configuration, corpus manifest hash, model, prompt version, and token counts.

## Environment

```sh
cp .env.example .env
```

Set at minimum:

- A non-default `POSTGRES_PASSWORD`.
- `LLM_API_KEY` for real-model runs, or `LLM_PROVIDER=fake` for smoke/CI.
- `DEMO_PASSCODE`, `SESSION_COOKIE_SECURE=true`, and `PUBLIC_ORIGIN=https://...` in production.

`.env` files are ignored. Do not commit keys, passcodes, database passwords, or provider responses containing secrets.

## Evaluation

```sh
.venv/bin/pip install -r eval/requirements.txt
.venv/bin/python eval/run.py --validate-only
POLICYPILOT_BASE_URL=http://localhost:8080/api/v1 .venv/bin/python eval/run.py
```

The evaluator calls the public API only. It creates an isolated session per case/system and compares `agent` with `baseline` when the comparison is meaningful. CASE-4 and CASE-8 are explicitly excluded from the baseline score because a fixed one-pass flow cannot clarify or retry.

Automated quote matching confirms provenance, not semantic entailment. Complete the manual source log in `docs/evaluation.md` before publishing final scores.

## Cost calculation

`eval/pricing.yaml` contains versioned estimates per million input/output tokens. Replace example rates with the provider's documented rate on the evaluation date and cite that source in the final result notes. The runner prefers backend-reported estimated cost and otherwise computes:

```text
(input_tokens × input_rate + output_tokens × output_rate) / 1,000,000
```

The final report includes cost per case and total agent/baseline cost. Public deployment also has an application daily budget and should use a provider-side capped project key.
