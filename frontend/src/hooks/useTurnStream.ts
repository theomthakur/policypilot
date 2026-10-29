import { useEffect, useRef, useState } from 'react'
import { api, turnEventsUrl } from '../api/client'
import type { AnswerPayload, RunTotals, TraceEvent } from '../api/types'

interface TurnStreamState {
  events: TraceEvent[]
  answer: AnswerPayload | null
  totals: RunTotals | null
  status: 'idle' | 'streaming' | 'polling' | 'completed' | 'failed'
  error: string | null
}

const initialState: TurnStreamState = {
  events: [],
  answer: null,
  totals: null,
  status: 'idle',
  error: null,
}

export function useTurnStream(turnId: string | null): TurnStreamState {
  const [state, setState] = useState<TurnStreamState>(initialState)
  const pollTimer = useRef<number | null>(null)

  useEffect(() => {
    if (!turnId) {
      setState(initialState)
      return
    }

    let cancelled = false
    let source: EventSource | null = null

    const finishPolling = () => {
      if (pollTimer.current !== null) window.clearTimeout(pollTimer.current)
      pollTimer.current = null
    }

    const poll = async () => {
      if (cancelled) return
      setState((current) => ({ ...current, status: 'polling' }))
      try {
        const turn = await api.getTurn(turnId)
        if (cancelled) return
        setState((current) => ({
          ...current,
          events: turn.trace.length > 0 ? turn.trace : current.events,
          answer: turn.answer ?? current.answer,
          totals: turn.totals ?? current.totals,
          status:
            turn.status === 'completed'
              ? 'completed'
              : turn.status === 'failed'
                ? 'failed'
                : 'polling',
          error:
            turn.status === 'failed'
              ? 'The turn could not be completed.'
              : null,
        }))
        if (turn.status === 'queued' || turn.status === 'running') {
          pollTimer.current = window.setTimeout(poll, 1000)
        }
      } catch (error) {
        if (!cancelled) {
          setState((current) => ({
            ...current,
            status: 'failed',
            error:
              error instanceof Error
                ? error.message
                : 'Unable to load this turn.',
          }))
        }
      }
    }

    setState({ ...initialState, status: 'streaming' })
    source = new EventSource(turnEventsUrl(turnId), { withCredentials: true })
    source.onmessage = (message) => {
      try {
        const event = JSON.parse(message.data) as TraceEvent
        setState((current) => ({
          ...current,
          events: [
            ...current.events.filter((item) => item.id !== event.id),
            event,
          ].sort((a, b) => a.sequence - b.sequence),
          answer: event.answer ?? current.answer,
          totals: event.totals ?? current.totals,
          status: event.type === 'answer' ? 'completed' : current.status,
        }))
        if (event.type === 'answer' || event.type === 'turn_failed') {
          source?.close()
        }
      } catch {
        setState((current) => ({
          ...current,
          error: 'A trace event was malformed.',
        }))
      }
    }
    source.onerror = () => {
      source?.close()
      void poll()
    }

    return () => {
      cancelled = true
      source?.close()
      finishPolling()
    }
  }, [turnId])

  return state
}
