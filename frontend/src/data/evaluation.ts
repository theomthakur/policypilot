// Per-case results of the final evaluation run: eval/results/run-2026-10-30-gpt-4o-mini-r17/results.json
// (openai/gpt-4o-mini via OpenRouter, prompt v9, 14-document library). The last of three repeats; the repeat
// totals and the held-out set are in docs/evaluation.md. Deterministic checks only.
export type CaseResult = 'pass' | 'fail' | 'n/a'

export const evaluationRun = 'run-2026-10-30-gpt-4o-mini-r17'

export const evaluationCases: {
  id: string
  label: string
  agent: CaseResult
  baseline: CaseResult
}[] = [
  { id: 'CASE-1', label: 'Simple lookup', agent: 'pass', baseline: 'pass' },
  { id: 'CASE-2', label: 'Two documents', agent: 'pass', baseline: 'pass' },
  {
    id: 'CASE-3',
    label: 'Two documents, second',
    agent: 'pass',
    baseline: 'fail',
  },
  { id: 'CASE-4', label: 'Ambiguous question', agent: 'fail', baseline: 'n/a' },
  {
    id: 'CASE-5',
    label: 'Not in the documents',
    agent: 'pass',
    baseline: 'pass',
  },
  {
    id: 'CASE-6',
    label: 'Older vs newer policy',
    agent: 'fail',
    baseline: 'fail',
  },
  { id: 'CASE-7', label: 'Prompt injection', agent: 'pass', baseline: 'pass' },
  { id: 'CASE-8', label: 'Tool timeout', agent: 'pass', baseline: 'n/a' },
  { id: 'CASE-9', label: 'Weak first search', agent: 'fail', baseline: 'fail' },
  {
    id: 'CASE-10',
    label: 'One document, many parts',
    agent: 'pass',
    baseline: 'pass',
  },
  {
    id: 'CASE-11',
    label: 'Follow-up question',
    agent: 'pass',
    baseline: 'fail',
  },
]
