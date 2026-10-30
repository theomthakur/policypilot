import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Turn } from '../api/types'
import { useTurnStream } from './useTurnStream'

const completed = (id: string, text: string): Turn => ({
  id,
  status: 'completed',
  stop_reason: 'answered',
  answer: {
    paragraphs: [text],
    claims: [],
    citations: [],
    notices: [],
    clarification: null,
  },
  trace: [],
  totals: null,
})

vi.mock('../api/client', () => ({
  api: {
    getTurn: vi.fn(async (id: string) => completed(id, `answer for ${id}`)),
  },
  turnEventsUrl: (id: string) => `/api/v1/turns/${id}/events`,
}))

class FakeEventSource {
  onerror: (() => void) | null = null
  addEventListener() {}
  close() {}
  constructor(public url: string) {
    // An immediate stream error makes the hook fall back to polling, which returns the finished turn.
    queueMicrotask(() => this.onerror?.())
  }
}

describe('useTurnStream', () => {
  beforeEach(() => {
    vi.stubGlobal('EventSource', FakeEventSource)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('never shows the previous turn answer for a new turn, even for one render', async () => {
    // Every render is recorded: the stale value only exists in the render before effects run.
    const renders: { id: string | null; answer: string | undefined }[] = []
    const { result, rerender } = renderHook(
      ({ id }) => {
        const stream = useTurnStream(id)
        renders.push({ id, answer: stream.answer?.paragraphs[0] })
        return stream
      },
      { initialProps: { id: 'a' as string | null } },
    )
    await waitFor(() =>
      expect(result.current.answer?.paragraphs).toEqual(['answer for a']),
    )

    rerender({ id: 'b' })
    await waitFor(() =>
      expect(result.current.answer?.paragraphs).toEqual(['answer for b']),
    )

    const forB = renders.filter((r) => r.id === 'b')
    expect(forB.length).toBeGreaterThan(0)
    expect(forB.some((r) => r.answer === 'answer for a')).toBe(false)
  })
})
