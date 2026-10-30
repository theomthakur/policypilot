import { describe, expect, it } from 'vitest'
import { eventStatusLabel, humanizeEvent, stopReasonLabel } from './humanize'

describe('plain-English trace wording', () => {
  it('describes searches and their results in words', () => {
    expect(
      humanizeEvent({
        type: 'tool_call',
        status: 'ok',
        tool: 'search_documents',
        input: { query: 'guest bandwidth' },
        summary: 'Calling search_documents.',
      }).text,
    ).toBe('Looking for “guest bandwidth” across the documents.')
    expect(
      humanizeEvent({
        type: 'tool_result',
        status: 'ok',
        tool: 'search_documents',
        summary: '',
        hits: 6,
        weak: true,
      }).text,
    ).toBe('Found 6 passages, but none looked convincing.')
    expect(
      humanizeEvent({
        type: 'tool_result',
        status: 'empty',
        tool: 'search_documents',
        summary: '',
        hits: 0,
      }).title,
    ).toBe('Found nothing')
  })

  it('hides the noise events and explains problems and limits', () => {
    expect(
      humanizeEvent({
        type: 'evaluate',
        status: 'info',
        summary: 'Model decided the next action.',
      }).hidden,
    ).toBe(true)
    expect(
      humanizeEvent({
        type: 'tool_result',
        status: 'error',
        summary: 'INVALID_ARGUMENT: x',
        tool: 'search_documents',
      }).text,
    ).toContain('malformed')
    expect(
      humanizeEvent({
        type: 'limit_reached',
        status: 'info',
        summary: '',
        limitName: 'time',
      }).text,
    ).toContain('Ran out of time')
  })

  it('labels the run result and event statuses for people', () => {
    expect(stopReasonLabel('insufficient_evidence')).toBe(
      'Not in the documents',
    )
    expect(stopReasonLabel('something_new')).toBe('something new')
    expect(eventStatusLabel('blocked')).toBe('skipped')
  })
})
