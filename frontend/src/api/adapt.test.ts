import { describe, expect, it } from 'vitest'
import {
  adaptAnswer,
  adaptDocument,
  adaptEvent,
  adaptHealth,
  adaptIngestion,
  adaptTurn,
} from './adapt'

describe('backend to view-model adapters', () => {
  it('maps document and ingestion vocabulary', () => {
    expect(
      adaptDocument({
        id: 'd1',
        title: 'T',
        filename: 'f.pdf',
        page_count: 3,
        status: 'processing',
        source: 'corpus',
      }),
    ).toMatchObject({ status: 'extracting', source: 'bundled' })
    expect(adaptDocument({ status: 'queued', source: 'upload' })).toMatchObject(
      {
        status: 'pending',
        source: 'uploaded',
      },
    )
    expect(
      adaptIngestion({
        id: 'r',
        status: 'running',
        stage: 'embedding',
        pages_done: 2,
        page_count: 4,
      }),
    ).toMatchObject({
      status: 'embedding',
      progress: 0.5,
    })
    expect(
      adaptIngestion({
        id: 'r',
        status: 'succeeded',
        stage: 'done',
        pages_done: 4,
        page_count: 4,
      }),
    ).toMatchObject({
      status: 'ready',
      progress: 1,
    })
  })

  it('turns string health checks into status objects', () => {
    const health = adaptHealth({
      status: 'degraded',
      version: '0.1.0',
      checks: { database: 'ok', redis: 'down', llm_config: 'missing' },
    })
    expect(health.checks.database.status).toBe('ok')
    expect(health.checks.redis.status).toBe('down')
    expect(health.checks.llm_config.status).toBe('degraded')
  })

  it('maps verified citations, claims and notices', () => {
    const answer = adaptAnswer(
      {
        summary: 'Guests get 10 Mbps.',
        claims: [{ text: 'Guests get 10 Mbps.', citation_indexes: [1] }],
        citations: [
          {
            index: 1,
            document_id: 'd1',
            title: 'Guest Policy',
            page: 3,
            quote: 'limited to 10 Mbps',
            verified: true,
            check: 'exact_quote',
          },
        ],
        notices: [
          { kind: 'assumption', text: 'Assumed guests.' },
          { kind: 'conflict', text: 'Two dates.' },
        ],
      },
      null,
    )
    expect(answer?.paragraphs).toEqual(['Guests get 10 Mbps.'])
    expect(answer?.citations[0]).toMatchObject({
      id: '1',
      number: 1,
      document_title: 'Guest Policy',
      validation_status: 'verified',
    })
    expect(answer?.claims[0].citation_ids).toEqual(['1'])
    expect(answer?.notices.map((n) => n.type)).toEqual(['warning', 'conflict'])
  })

  it('turns a clarification into the clarification payload', () => {
    const answer = adaptAnswer(null, {
      question: 'Which account?',
      options: ['Student', 'Staff'],
    })
    expect(answer?.clarification).toEqual({
      prompt: 'Which account?',
      options: ['Student', 'Staff'],
    })
  })

  it('maps trace events including revisions, retries and result pages', () => {
    const search = adaptEvent({
      turn_id: 't',
      seq: 4,
      ts: '2026-10-29T20:00:00Z',
      type: 'tool_result',
      status: 'weak',
      tool: 'search_documents',
      summary: '6 hits (weak)',
      duration_ms: 40,
      result: {
        hits: 6,
        weak: true,
        pages: [
          { document_id: 'd1', title: 'A', page: 1 },
          { document_id: 'd1', title: 'A', page: 2 },
        ],
      },
    })
    expect(search).toMatchObject({
      id: 't-4',
      sequence: 4,
      status: 'empty',
      tool_name: 'search_documents',
    })
    expect(search.result?.documents).toEqual([
      { id: 'd1', title: 'A', pages: [1, 2] },
    ])
    const revised = adaptEvent({
      turn_id: 't',
      seq: 5,
      ts: '',
      type: 'query_revised',
      status: 'info',
      summary: 'Weak results.',
      revision: { previous_query: 'a', new_query: 'b', reason: 'low_score' },
    })
    expect(revised.summary).toContain('"a" → "b"')
    expect(
      adaptEvent({
        turn_id: 't',
        seq: 6,
        ts: '',
        type: 'tool_result',
        status: 'retried',
        summary: '',
      }).type,
    ).toBe('retry')
    expect(
      adaptEvent({
        turn_id: 't',
        seq: 7,
        ts: '',
        type: 'evaluate',
        status: 'info',
        summary: '',
        tokens: { prompt: 10, completion: 2 },
      }),
    ).toMatchObject({
      type: 'evidence_assessment',
      prompt_tokens: 10,
      completion_tokens: 2,
    })
  })

  it('adapts a whole turn with totals and stop reason', () => {
    const turn = adaptTurn({
      id: 'x',
      status: 'completed',
      stop_reason: 'answered',
      answer: { summary: 'S', claims: [], citations: [], notices: [] },
      events: [
        {
          turn_id: 'x',
          seq: 0,
          ts: '',
          type: 'turn_started',
          status: 'info',
          summary: 'Go',
        },
      ],
      totals: {
        steps: 3,
        tool_calls: 1,
        prompt_tokens: 100,
        completion_tokens: 20,
        estimated_cost_usd: 0.001,
        latency_ms: 900,
      },
    })
    expect(turn.status).toBe('completed')
    expect(turn.trace).toHaveLength(1)
    expect(turn.totals).toMatchObject({
      steps: 3,
      stop_reason: 'answered',
      estimated_cost_usd: 0.001,
    })
  })
})
