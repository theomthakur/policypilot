# Demo walkthrough

A reproducible walkthrough of the four moments the brief asks for: a multi-document question, evidence-driven re-retrieval, a clarification that keeps context, and a failed tool call handled within limits. It runs on the local Docker Compose stack. The recorded video is linked at the end.

**Target length:** 5 minutes. Saved traces and the resulting answers for each moment are in [`demo-evidence/`](demo-evidence/), so every step can be checked without a live model.

## Preparation

1. Start the stack: `docker compose up -d`, then open http://localhost:8080. Confirm the Knowledge base shows 14 ready documents (10 university policies, 4 NIST references).
2. Switch **Developer** mode on (the code icon at the bottom of the sidebar) so the run totals show: steps, searches, tokens, time and cost.
3. Click **New session**, then the **Agent activity** tab to watch the trace.
4. Keep keys, `.env` files and the demo passcode off the screen.

## 1. Multi-document grounded answer

Ask:

> A researcher has Level 3 confidential pre-publication data. What encryption is required at rest, and may the researcher paste it into a public consumer AI tool?

Show:
- The plan and the searches in the Agent activity tab (no private reasoning is shown).
- Evidence from two documents, Data Classification and Generative AI Guidance.
- At least two numbered citation chips. Click one to show the exact quote on the page, then **View** to open the PDF at that page.
- The run totals.

Saved: `demo-evidence/01-multi-document.md`.

## 2. Evidence-driven re-retrieval

Ask:

> For a Level 4 breach discovered by a remote worker, how quickly must it be reported and who must approve a split-tunnel VPN exception?

Show, in the Agent activity tab:
- The first search finds the breach-reporting rule but nothing about VPN exceptions.
- A **revised search** ("Searching again for what the first results did not cover"): the agent noticed which part was still unanswered and changed its next action because of what it had found.
- It then **reads the two full pages** instead of relying on excerpts, and answers from two documents.

This passes in every evaluation run. Say plainly what the revision is: in real runs, the agent's second search almost always targets a part of the question the first results did not cover. A rewrite after a *weak* first result is covered by a scripted test (`test_weak_search_triggers_a_visible_revised_query`), because the real model rarely gets a weak first result on this corpus.

Saved: `demo-evidence/02-re-retrieval.md`. The demonstrated re-retrieval flow is a saved trace rather than part of the normal walkthrough.

## 3. Clarification with retained context

Ask:

> How do I renew my Northfield account?

The agent asks which account type. Reply:

> I am a sponsored guest whose six-month account expires next month.

Show that the answer combines the original question with the reply and cites Account Lifecycle page 4 (the sponsor submits the renewal form 14 business days before expiry).

Saved: `demo-evidence/03-clarification.md`.

## 4. Failed tool call, handled within limits

This can't be triggered from the app. It is exercised by the evaluation with an injected fault (`FAULT_INJECTION_ENABLED=true`, test environments only, never public). Show the saved trace in `demo-evidence/04-tool-failure.md`: the first `search_documents` call times out, there is exactly one retry, the search recovers and the answer (35-day retention) is cited, all inside the limits.

To run it yourself: `python eval/run.py --case CASE-8`.

## Optional: Redis outage

Run `./scripts/redis_outage.sh`. Readiness changes to `degraded`, a question is still answered from PostgreSQL without the cache, and Redis is restarted. Use the saved output in `docs/deployment-evidence/` if changing live services during the recording feels risky.

## Closing points

- PostgreSQL holds everything durable; Redis speeds up things that are safe to lose.
- The baseline uses the same model and the same retrieval, but searches once and answers once. The agent helps on cross-document, follow-up and wording-mismatch questions and costs more on direct lookups.
- Results are in `docs/evaluation.md`, with the failures and the fact that no question set is blind.
- What is not solved, and what comes next: `docs/summary.md`.

## Recording checklist

- [ ] Multi-document answer with page citations
- [ ] A revised search driven by a result
- [ ] Clarification and the follow-up that keeps context
- [ ] The failed tool call and its bounded retry (saved trace)
- [ ] No keys, passcodes or private information visible

**Video:** to be added here before submission.
