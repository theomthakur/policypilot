import { useEffect, useRef, useState } from 'react'
import type { AnswerPayload, Citation } from '../api/types'
import { ClarificationCard } from './ClarificationCard'
import { AnimatedMark } from './AnimatedMark'
import { PolicyPilotMark } from './PolicyPilotMark'

export interface DisplayMessage {
  id: string
  role: 'user' | 'assistant'
  text?: string
  answer?: AnswerPayload | null
  meta?: string
}

interface ConversationPanelProps {
  messages: DisplayMessage[]
  busy: boolean
  streamLabel: string | null
  sessionReady: boolean
  mode: 'agent' | 'baseline'
  developer: boolean
  onModeChange: (mode: 'agent' | 'baseline') => void
  onSend: (content: string, replyToClarification?: boolean) => void
  onCitationOpen: (citation: Citation) => void
}

const examples = [
  'What MFA rules apply to remote research access?',
  'Compare the storage rules for restricted data and approved AI tools.',
  'What changed in the latest access policy bulletin?',
]

function AnswerView({
  answer,
  onCitationOpen,
}: {
  answer: AnswerPayload
  onCitationOpen: (citation: Citation) => void
}) {
  return (
    <div className="answer-view">
      {answer.notices.map((notice, index) => (
        <div
          className={`answer-notice notice-${notice.type}`}
          key={`${notice.type}-${index}`}
        >
          <strong>{notice.type.replaceAll('_', ' ')}</strong>
          <span>{notice.message}</span>
        </div>
      ))}
      {answer.paragraphs.map((paragraph, index) => (
        <p key={index}>{paragraph}</p>
      ))}
      {answer.citations.length > 0 && (
        <div className="citation-list" aria-label="Answer citations">
          {answer.citations.map((citation) => (
            <button
              key={citation.id}
              className="citation-chip"
              type="button"
              onClick={() => onCitationOpen(citation)}
              aria-label={`Open citation ${citation.number}: ${citation.document_title}, page ${citation.page}`}
            >
              <span>[{citation.number}]</span> {citation.document_title} · p.{' '}
              {citation.page}
              {citation.validation_status === 'verified' && (
                <span className="verified-check" aria-label="Verified">
                  ✓
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export function ConversationPanel({
  messages,
  busy,
  streamLabel,
  sessionReady,
  mode,
  developer,
  onModeChange,
  onSend,
  onCitationOpen,
}: ConversationPanelProps) {
  const [content, setContent] = useState('')
  const endRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [busy, messages])

  const submit = () => {
    const value = content.trim()
    if (!value || busy || !sessionReady) return
    onSend(value)
    setContent('')
  }

  const lastClarification = [...messages]
    .reverse()
    .find(
      (message) =>
        message.role === 'assistant' && message.answer?.clarification,
    )

  return (
    <section
      className="panel conversation-panel"
      aria-labelledby="conversation-title"
    >
      <div className="panel-heading conversation-heading">
        <div>
          <p className="eyebrow">Grounded policy assistant</p>
          <h2 id="conversation-title">Conversation</h2>
        </div>
        {developer && (
          <div className="mode-toggle" aria-label="Answer mode">
            <button
              className={mode === 'agent' ? 'active' : ''}
              type="button"
              onClick={() => onModeChange('agent')}
            >
              Agent
            </button>
            <button
              className={mode === 'baseline' ? 'active' : ''}
              type="button"
              onClick={() => onModeChange('baseline')}
            >
              Quick
            </button>
          </div>
        )}
      </div>
      {developer && (
        <p className="mode-hint">
          {mode === 'agent' ? (
            <>
              <strong>Agent:</strong> searches, searches again with different
              words when unsure, asks you when your question is unclear, and
              checks every quote. Slower, more careful.
            </>
          ) : (
            <>
              <strong>Quick:</strong> searches once and answers once, with the
              same quote check. Faster, and the simple version the agent is
              compared against.
            </>
          )}
        </p>
      )}

      <div className="messages" aria-live="polite">
        {messages.length === 0 && (
          <div className="welcome-state">
            <div className="assistant-avatar large" aria-hidden="true">
              <PolicyPilotMark />
            </div>
            <p className="welcome-kicker">Policy intelligence, with evidence</p>
            <h3>Ask across your policy library</h3>
            <p>
              I will search the corpus, inspect evidence, and cite the pages
              that support the answer.
            </p>
            <div className="example-prompts">
              {examples.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => {
                    setContent(example)
                    inputRef.current?.focus()
                  }}
                >
                  <span>{example}</span>
                  <span aria-hidden="true">↗</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <article
            className={`message message-${message.role}`}
            key={message.id}
          >
            <div
              className={
                message.role === 'assistant'
                  ? 'assistant-avatar'
                  : 'user-avatar'
              }
              aria-hidden="true"
            >
              {message.role === 'assistant' ? <PolicyPilotMark /> : 'You'}
            </div>
            <div className="message-content">
              <span className="message-author">
                {message.role === 'assistant' ? 'PolicyPilot' : 'You'}
              </span>
              {message.meta && (
                <span className="message-meta">{message.meta}</span>
              )}
              {message.text && <p>{message.text}</p>}
              {message.answer && (
                <AnswerView
                  answer={message.answer}
                  onCitationOpen={onCitationOpen}
                />
              )}
            </div>
          </article>
        ))}

        {busy && (
          <article className="message message-assistant working-message">
            <div className="assistant-avatar" aria-hidden="true">
              <AnimatedMark speed={1.4} />
            </div>
            <div className="message-content">
              <span className="message-author">PolicyPilot</span>
              <p>
                <span className="thinking-dots">
                  <i />
                  <i />
                  <i />
                </span>
                {streamLabel ?? 'Inspecting evidence…'}
              </p>
            </div>
          </article>
        )}

        {lastClarification?.answer?.clarification && !busy && (
          <ClarificationCard
            clarification={lastClarification.answer.clarification}
            onReply={(reply) => onSend(reply, true)}
          />
        )}
        <div ref={endRef} />
      </div>

      <div className="composer-wrap">
        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault()
            submit()
          }}
        >
          <label className="visually-hidden" htmlFor="question">
            Ask a policy question
          </label>
          <textarea
            ref={inputRef}
            id="question"
            rows={2}
            value={content}
            disabled={busy || !sessionReady}
            placeholder={
              sessionReady
                ? 'Ask a question about the policy documents…'
                : 'Starting a secure session…'
            }
            onChange={(event) => setContent(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                submit()
              }
            }}
          />
          <button
            className="send-button"
            type="submit"
            disabled={busy || !sessionReady || content.trim().length === 0}
            aria-label="Send question"
          >
            ↑
          </button>
        </form>
        <p>
          Answers are limited to indexed evidence. Verify important decisions
          against the cited source.
        </p>
      </div>
    </section>
  )
}
