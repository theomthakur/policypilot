import { useEffect, useRef, useState } from 'react'
import { api, turnEventsUrl } from '../api/client'
import { adaptEvent } from '../api/adapt'
import type { AnswerPayload, RunTotals, TraceEvent } from '../api/types'

interface TurnStreamState {
  /** The turn this state belongs to; a different turn id means the state is stale. */
  turnId: string | null
  events: TraceEvent[]
  answer: AnswerPayload | null
  totals: RunTotals | null
  status: 'idle' | 'streaming' | 'polling' | 'completed' | 'failed'
  error: string | null
}

const initialState: TurnStreamState = {
  turnId: null,
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

    // The server names each SSE frame after the trace event type, so `onmessage` never fires;
    // listen for every type and close once the turn is complete.
    const eventNames = [
      'turn_started',
      'plan',
      'tool_call',
      'tool_result',
      'evaluate',
      'query_revised',
      'clarification_requested',
      'synthesize',
      'verify',
      'answer',
      'limit_reached',
      'injection_flagged',
      'turn_completed',
    ]
    const finish = async () => {
      source?.close()
      try {
        const turn = await api.getTurn(turnId)
        if (cancelled) return
        setState((current) => ({
          turnId: current.turnId,
          events: turn.trace.length > 0 ? turn.trace : current.events,
          answer: turn.answer ?? current.answer,
          totals: turn.totals ?? current.totals,
          status: turn.status === 'failed' ? 'failed' : 'completed',
          error:
            turn.status === 'failed'
              ? 'The turn could not be completed.'
              : null,
        }))
      } catch {
        void poll()
      }
    }
    const onEvent = (message: MessageEvent<string>) => {
      try {
        const event = adaptEvent(JSON.parse(message.data))
        setState((current) => ({
          ...current,
          events: [
            ...current.events.filter((item) => item.id !== event.id),
            event,
          ].sort((a, b) => a.sequence - b.sequence),
        }))
        if (message.type === 'turn_completed') void finish()
      } catch {
        setState((current) => ({
          ...current,
          error: 'A trace event was malformed.',
        }))
      }
    }

    setState({ ...initialState, turnId, status: 'streaming' })
    source = new EventSource(turnEventsUrl(turnId), { withCredentials: true })
    eventNames.forEach((name) =>
      source?.addEventListener(name, onEvent as EventListener),
    )
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

  // Right after a new turn id arrives, state still belongs to the previous turn for one render. Showing
  // it would attach the previous answer to the new question, so a mismatch reads as a fresh turn.
  if (state.turnId === turnId) return state
  return turnId ? { ...initialState, turnId, status: 'streaming' } : initialState
}
