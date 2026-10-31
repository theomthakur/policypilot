# PolicyPilot evaluation report

- Run ID: `20261031T120545Z`
- Started: 2026-10-31T12:05:45.249533+00:00
- API: `http://localhost:8080/api/v1`
- Corpus: `northfield-it-policies-v1`

## Comparison

| Case | Category | Agent | Baseline | Agent tools | Baseline tools | Agent latency | Baseline latency |
|---|---|---:|---:|---:|---:|---:|---:|
| HELD-1 | simple_lookup | pass | pass | 3 | 1 | 5754 ms | 1671 ms |
| HELD-2 | simple_lookup | fail | fail | 4 | 1 | 12778 ms | 1182 ms |
| HELD-3 | multi_document | pass | pass | 5 | 1 | 8086 ms | 1865 ms |
| HELD-4 | ambiguous | pass | n/a | 3 | n/a | 5935 ms | n/a ms |
| HELD-5 | insufficient_evidence | pass | pass | 6 | 1 | 7899 ms | 931 ms |
| HELD-6 | insufficient_evidence | pass | pass | 6 | 1 | 8771 ms | 950 ms |
| HELD-7 | conflict | fail | fail | 4 | 1 | 10246 ms | 2054 ms |
| HELD-8 | follow_up | fail | fail | 7 | 2 | 13287 ms | 2243 ms |
| HELD-9 | adaptive_retrieval | fail | pass | 3 | 1 | 5820 ms | 1182 ms |
| HELD-10 | simple_lookup | pass | pass | 2 | 1 | 5006 ms | 1317 ms |

## Case notes

### HELD-1: Answer the stated lockout threshold and first lockout period without asking anything.

- **agent: pass.** All deterministic checks passed; manual source review is still required.
- **baseline: pass.** All deterministic checks passed; manual source review is still required.

### HELD-2: Answer from the research computing governance policy (the only inactivity rule; it covers research computing accounts) without asking which account type.

- **agent: fail.** Failed deterministic checks: required_fact:180 days, expected_sources
- **baseline: fail.** Failed deterministic checks: required_fact:180 days, stop_reason, distinct_documents_cited, expected_sources

### HELD-3: Combine the identity standard's enrollment window with the remote-work standard's MFA product.

- **agent: pass.** All deterministic checks passed; manual source review is still required.
- **baseline: pass.** All deterministic checks passed; manual source review is still required.

### HELD-4: Ask which kind of storage is meant, then answer the home directory quota.

- **agent: pass.** All deterministic checks passed; manual source review is still required.
- **baseline: n/a.** A retrieve-once baseline has no clarification action or retained conversational state.

### HELD-5: State that the documents do not cover vacation days; invent nothing.

- **agent: pass.** All deterministic checks passed; manual source review is still required.
- **baseline: pass.** All deterministic checks passed; manual source review is still required.

### HELD-6: State that no fine schedule exists in the documents; invent no amount.

- **agent: pass.** All deterministic checks passed; manual source review is still required.
- **baseline: pass.** All deterministic checks passed; manual source review is still required.

### HELD-7: Cite the 2023 policy (not universally mandated) and the 2025 standard (required for all accounts) and explain the difference.

- **agent: fail.** Failed deterministic checks: required_fact:2023, distinct_documents_cited, notice_kind, expected_sources
- **baseline: fail.** Failed deterministic checks: required_fact:2023, required_fact:2025, notice_kind, expected_sources

### HELD-8: Resolve "standard buckets" in the context of audit record retention and answer one year.

- **agent: fail.** Failed deterministic checks: stop_reason
- **baseline: fail.** Failed deterministic checks: required_fact:one year|1 year|12 months, stop_reason, distinct_documents_cited, expected_sources

### HELD-9: Find the scratch storage purge period despite the different everyday wording.

- **agent: fail.** Failed deterministic checks: required_fact:60, expected_sources
- **baseline: pass.** All deterministic checks passed; manual source review is still required.

### HELD-10: Answer the snapshot retention period from the research computing governance policy.

- **agent: pass.** All deterministic checks passed; manual source review is still required.
- **baseline: pass.** All deterministic checks passed; manual source review is still required.

## Interpretation

Deterministic checks measure required facts, prohibited text, citations, stop behavior, tool limits, and observable adaptive actions. They do not prove semantic entailment. Complete the manual page-check log before treating citation support as final.

The agent should be judged on whether iteration improves completion or grounding for each case, while tool calls, latency, token use, and cost show its overhead. The report does not assume the agent wins every case.
