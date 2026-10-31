# PolicyPilot evaluation report

- Run ID: `20261031T120241Z`
- Started: 2026-10-31T12:02:41.631142+00:00
- API: `http://localhost:8080/api/v1`
- Corpus: `northfield-it-policies-v1`

## Comparison

| Case | Category | Agent | Baseline | Agent tools | Baseline tools | Agent latency | Baseline latency |
|---|---|---:|---:|---:|---:|---:|---:|
| HELD-11 | conflict | pass | fail | 3 | 1 | 14545 ms | 1465 ms |
| HELD-12 | conflict | pass | fail | 3 | 1 | 5155 ms | 1706 ms |
| HELD-13 | conflict | pass | pass | 2 | 1 | 5308 ms | 1225 ms |
| HELD-14 | simple_lookup | pass | pass | 2 | 1 | 5745 ms | 1510 ms |
| HELD-15 | ambiguous | pass | n/a | 3 | n/a | 6504 ms | n/a ms |
| HELD-16 | ambiguous | pass | n/a | 3 | n/a | 5744 ms | n/a ms |
| HELD-17 | simple_lookup | pass | pass | 2 | 1 | 5518 ms | 1570 ms |
| HELD-18 | simple_lookup | pass | pass | 3 | 1 | 6332 ms | 1189 ms |
| HELD-19 | simple_lookup | pass | pass | 3 | 1 | 5113 ms | 1626 ms |

## Case notes

### HELD-11: Current rule from the 2025 standard (no periodic expiration), with the earlier schedule and the conflict explained.

- **agent: pass.** All deterministic checks passed; manual source review is still required.
- **baseline: fail.** Failed deterministic checks: required_fact:2025, required_fact:prohibit|no longer|not required|supersed, distinct_documents_cited, notice_kind, expected_sources

### HELD-12: A historical question: answer the 2023 rule without presenting it as current.

- **agent: pass.** All deterministic checks passed; manual source review is still required.
- **baseline: fail.** Failed deterministic checks: required_fact:90 days, expected_sources

### HELD-13: Service accounts are explicitly outside what the 2025 standard supersedes; the 2023 rule (90 days) still applies and no supersession is claimed.

- **agent: pass.** All deterministic checks passed; manual source review is still required.
- **baseline: pass.** All deterministic checks passed; manual source review is still required.

### HELD-14: Answer 20 characters from the password policy; nothing is superseded here.

- **agent: pass.** All deterministic checks passed; manual source review is still required.
- **baseline: pass.** All deterministic checks passed; manual source review is still required.

### HELD-15: Ask which storage is meant (the documents give different backup rules for home, project, scratch and archive storage), then answer for project storage.

- **agent: pass.** All deterministic checks passed; manual source review is still required.
- **baseline: n/a.** A retrieve-once baseline has no clarification action or retained conversational state.

### HELD-16: Ask which service is meant (Research Vault and the managed object stores keep deleted files for different periods), then answer for Research Vault.

- **agent: pass.** All deterministic checks passed; manual source review is still required.
- **baseline: n/a.** A retrieve-once baseline has no clarification action or retained conversational state.

### HELD-17: Answer AES-256 without asking which kind of data or system.

- **agent: pass.** All deterministic checks passed; manual source review is still required.
- **baseline: pass.** All deterministic checks passed; manual source review is still required.

### HELD-18: Answer 24 hours without asking.

- **agent: pass.** All deterministic checks passed; manual source review is still required.
- **baseline: pass.** All deterministic checks passed; manual source review is still required.

### HELD-19: No backup; deleted seven days after upload. Answer without asking.

- **agent: pass.** All deterministic checks passed; manual source review is still required.
- **baseline: pass.** All deterministic checks passed; manual source review is still required.

## Interpretation

Deterministic checks measure required facts, prohibited text, citations, stop behavior, tool limits, and observable adaptive actions. They do not prove semantic entailment. Complete the manual page-check log before treating citation support as final.

The agent should be judged on whether iteration improves completion or grounding for each case, while tool calls, latency, token use, and cost show its overhead. The report does not assume the agent wins every case.
