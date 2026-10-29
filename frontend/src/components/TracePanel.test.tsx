import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { RunTotals, TraceEvent } from '../api/types'
import { TracePanel } from './TracePanel'

const event: TraceEvent = {
  id: 'event-1',
  sequence: 1,
  type: 'query_revised',
  timestamp: '2026-10-29T20:00:00Z',
  status: 'ok',
  summary: 'Changed the query after weak evidence.',
  input: { query: 'approved remote research access' },
  duration_ms: 12,
}

const totals: RunTotals = {
  steps: 4,
  tool_calls: 2,
  prompt_tokens: 100,
  completion_tokens: 50,
  estimated_cost_usd: 0.0012,
  latency_ms: 2400,
  stop_reason: 'answer_complete',
}

describe('TracePanel', () => {
  it('renders adaptive action badges and run totals', () => {
    render(
      <TracePanel events={[event]} totals={totals} streamStatus="completed" />,
    )

    expect(screen.getByText('Query revised')).toBeInTheDocument()
    expect(
      screen.getByText('Changed the query after weak evidence.'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Run totals')).toHaveTextContent('150tokens')
    expect(screen.getByLabelText('Run totals')).toHaveTextContent(
      'answer complete',
    )
  })
})
