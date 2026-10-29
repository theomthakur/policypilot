# Demo walkthrough

Target recording length: 5–7 minutes. Use the deployed release and keep a terminal ready for the controlled Redis/tool-failure demonstrations. Pre-index the bundled corpus.

## Preparation

1. Open the public URL in a clean browser and pass the demo access gate.
2. Confirm the document panel shows ten ready synthetic PDFs.
3. Open the trace panel and clear/create a new session.
4. Keep `eval/cases.yaml` and one generated PDF ready for source verification.
5. Do not expose `.env`, keys, passcodes, provider dashboards, or private prompts.

## 1. Multi-document grounded answer

Ask CASE-2:

> A researcher has Level 3 confidential pre-publication data. What encryption is required at rest, and may the researcher paste it into a public consumer AI tool?

Show:

- The plan/tool events without chain-of-thought.
- Evidence from Data Classification and Generative AI Guidance.
- At least two verified citation chips.
- The citation drawer with the exact highlighted page quote.
- Run totals: tool calls, latency, tokens, and estimated cost.

## 2. Evidence-driven re-retrieval

Ask CASE-9:

> Where may I keep highly sensitive clinical study files in an internet-hosted file repository?

Show:

- The weak first result.
- The `query_revised` trace event and the reason for changing action.
- A follow-up search/read using corpus terms such as Level 4 or controlled analytics enclave.
- The grounded final answer and pages.

Emphasize that the next action changed because of observed results; this is not a fixed retrieve-then-generate pipeline.

## 3. Clarification with retained context

Ask:

> How do I renew my Northfield account?

The agent should ask which account type. Select or type:

> I am a sponsored guest whose six-month account expires next month.

Show that the next answer uses the original renewal question plus the clarification and cites Account Lifecycle page 3.

## 4. Controlled tool timeout

Run CASE-8 through the evaluator or test-only demo control with `FAULT_INJECTION_ENABLED=true` in a non-public evaluation environment. Never enable arbitrary fault injection on the public deployment.

Show:

- First `search_documents` timeout.
- Exactly one retry.
- Recovery and a cited 35-day answer, or a bounded partial response if recovery is configured to fail.
- Stop reason and total duration within limits.

## Optional resilience clip

Run `./scripts/redis_outage.sh`. Show readiness become `degraded`, a question continue via the PostgreSQL/uncached fallback, and Redis restart. Use saved redacted output if changing live infrastructure during the recording is risky.

## Closing points

- PostgreSQL holds durable records; Redis accelerates replaceable state.
- The baseline uses the same model and retriever but searches exactly once.
- Evaluation reports successes, failures, latency, tokens, and cost rather than assuming the agent always wins.
- The deployment is intentionally one VM for reproducibility; explain the documented scaling path.

## Recording checklist

- [ ] Public URL and release version visible.
- [ ] Multi-document answer and page citations.
- [ ] Result-driven revised action.
- [ ] Clarification and follow-up context.
- [ ] Failed tool call with bounded handling.
- [ ] No secrets or private information visible.
- [ ] Video link added here before submission.

**Video:** pending final deployed release.
