import { eventStatusLabel, stopReasonLabel } from '../api/humanize'
import type { RunTotals, TraceEvent, TraceEventType } from '../api/types'

interface TracePanelProps {
  events: TraceEvent[]
  totals: RunTotals | null
  streamStatus: 'idle' | 'streaming' | 'polling' | 'completed' | 'failed'
}

const badgeTypes: Partial<Record<TraceEventType, string>> = {
  query_revised: 'Query revised',
  retry: 'Retry',
  timeout: 'Timeout',
  injection_flagged: 'Injection flagged',
  limit_reached: 'Limit reached',
}

function EventIcon({ event }: { event: TraceEvent }) {
  const icon =
    event.type === 'tool_call'
      ? '⌘'
      : event.type === 'answer'
        ? '✓'
        : event.type === 'turn_failed'
          ? '!'
          : '·'
  return (
    <span className={`event-icon event-${event.status}`} aria-hidden="true">
      {icon}
    </span>
  )
}

export function TracePanel({ events, totals, streamStatus }: TracePanelProps) {
  return (
    <section className="panel trace-panel" aria-labelledby="trace-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Observable, not hidden reasoning</p>
          <h2 id="trace-title">Execution trace</h2>
        </div>
        {streamStatus !== 'idle' && (
          <span className={`stream-state stream-${streamStatus}`}>
            {(streamStatus === 'streaming' || streamStatus === 'polling') && (
              <span className="live-dot" />
            )}
            {streamStatus}
          </span>
        )}
      </div>

      {events.length === 0 ? (
        <div className="trace-empty">
          <div className="trace-empty-icon" aria-hidden="true">
            ◎
          </div>
          <strong>The agent’s actions will appear here</strong>
          <span>
            Ask a question to see searches, evidence checks, revisions, and
            stopping conditions.
          </span>
        </div>
      ) : (
        <ol className="trace-list">
          {events
            .filter((event) => !event.hidden)
            .map((event) => (
              <li key={event.id} className="trace-event">
                <EventIcon event={event} />
                <div className="event-body">
                  <div className="event-title-row">
                    <strong>
                      {event.title ??
                        event.tool_name ??
                        event.type.replaceAll('_', ' ')}
                    </strong>
                    {badgeTypes[event.type] && (
                      <span className={`trace-badge badge-${event.type}`}>
                        {badgeTypes[event.type]}
                      </span>
                    )}
                    {event.duration_ms != null && (
                      <time>{event.duration_ms} ms</time>
                    )}
                  </div>
                  <p>{event.summary}</p>
                  {event.input && (
                    <details>
                      <summary>Technical details</summary>
                      <pre>
                        {event.tool_name ? `${event.tool_name}\n` : ''}
                        {JSON.stringify(event.input, null, 2)}
                      </pre>
                    </details>
                  )}
                  {event.result?.documents &&
                    event.result.documents.length > 0 && (
                      <div className="source-pills">
                        {event.result.documents.map((document) => (
                          <span key={`${event.id}-${document.id}`}>
                            {document.title} · p. {document.pages.join(', ')}
                          </span>
                        ))}
                      </div>
                    )}
                  <span className={`event-status status-label-${event.status}`}>
                    {eventStatusLabel(event.status)}
                  </span>
                </div>
              </li>
            ))}
        </ol>
      )}

      {totals && (
        <div className="run-totals" aria-label="Run totals">
          <div>
            <strong>{totals.steps}</strong>
            <span>steps</span>
          </div>
          <div>
            <strong>{totals.tool_calls}</strong>
            <span>searches</span>
          </div>
          <div>
            <strong>{totals.prompt_tokens + totals.completion_tokens}</strong>
            <span>tokens</span>
          </div>
          <div>
            <strong>{(totals.latency_ms / 1000).toFixed(1)}s</strong>
            <span>time</span>
          </div>
          <div>
            <strong>${totals.estimated_cost_usd.toFixed(4)}</strong>
            <span>cost</span>
          </div>
          <div>
            <strong>{stopReasonLabel(totals.stop_reason)}</strong>
            <span>result</span>
          </div>
        </div>
      )}
    </section>
  )
}
