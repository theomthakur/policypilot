import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { AnswerPayload, Citation } from '../api/types'
import { ClarificationCard } from './ClarificationCard'
import { AnimatedMark } from './AnimatedMark'
import { RichText } from './formatText'
import { UserAvatar } from './UserAvatar'
import { personalizedGreeting } from '../api/greeting'
import { PolicyPilotMark } from './PolicyPilotMark'
import {
  isClarificationReply,
  latestPendingClarification,
} from './conversationState'

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
  firstName: string | null
  onModeChange: (mode: 'agent' | 'baseline') => void
  onSend: (content: string, replyToClarification?: boolean) => void
  onCitationOpen: (citation: Citation) => void
}

const examples = [
  'What MFA rules apply to remote research access?',
  'Compare storage rules for restricted data and AI tools',
  'How do I renew a sponsored guest account?',
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
      {answer.paragraphs.length > 0 && (
        <div className="answer-bubble">
          {answer.paragraphs.map((paragraph, index) => (
            <RichText key={index} text={paragraph} />
          ))}
        </div>
      )}
      {answer.notices.map((notice, index) => (
        <div
          className={`answer-notice notice-${notice.type}`}
          key={`${notice.type}-${index}`}
        >
          <strong>{notice.type.replaceAll('_', ' ')}</strong>
          <span>{notice.message}</span>
        </div>
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

const followUps = ['What else should I know?', 'Explain that in simpler words']

function lastAnswerHasSources(messages: DisplayMessage[]): boolean {
  const last = messages.at(-1)
  return Boolean(
    last?.role === 'assistant' &&
      last.answer &&
      !last.answer.clarification &&
      last.answer.citations.length > 0,
  )
}

function CopyButton({ answer }: { answer: AnswerPayload }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    const sources = answer.citations
      .map((c) => `[${c.number}] ${c.document_title}, p. ${c.page}`)
      .join('\n')
    const text = [
      answer.paragraphs.join('\n\n'),
      sources && `Sources:\n${sources}`,
    ]
      .filter(Boolean)
      .join('\n\n')
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      // Clipboard access can be blocked; the answer is still selectable.
    }
  }
  return (
    <button
      type="button"
      className={`copy-button${copied ? ' is-copied' : ''}`}
      onClick={() => void copy()}
      aria-label={copied ? 'Copied to clipboard' : 'Copy answer'}
    >
      {copied ? (
        <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
          <path
            d="M3.5 8.5l3 3 6-7"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ) : (
        <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
          <rect
            x="5.5"
            y="5.5"
            width="8"
            height="8"
            rx="1.8"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.4"
          />
          <path
            d="M10.5 3.8V3.5A1.8 1.8 0 0 0 8.7 1.7H3.5A1.8 1.8 0 0 0 1.7 3.5v5.2a1.8 1.8 0 0 0 1.8 1.8h.3"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
        </svg>
      )}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

export function ConversationPanel({
  messages,
  busy,
  streamLabel,
  sessionReady,
  mode,
  developer,
  firstName,
  onModeChange,
  onSend,
  onCitationOpen,
}: ConversationPanelProps) {
  const [content, setContent] = useState('')
  const endRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Keep the newest content in view without the page jumping: new messages scroll smoothly,
  // and the one-line status below changes in place instead of pushing the conversation down.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length])
  useLayoutEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [busy, streamLabel])

  // The box is one line tall and grows with what is typed, so the text and the send button stay centred.
  useLayoutEffect(() => {
    const box = inputRef.current
    if (!box) return
    box.style.height = 'auto'
    box.style.height = `${Math.min(box.scrollHeight, 140)}px`
  }, [content])

  const submit = () => {
    const value = content.trim()
    if (!value || busy || !sessionReady) return
    onSend(value)
    setContent('')
  }

  // A clarification is actionable only until the next turn completes. Looking through the full transcript
  // left resolved cards clickable, which could submit the same choice twice.
  const lastClarification = latestPendingClarification(messages)

  return (
    <section
      className={`panel conversation-panel${messages.length === 0 ? ' is-empty' : ''}`}
      aria-label="Conversation"
    >
      <div className="panel-heading conversation-heading">
        <div
          className={`mode-toggle${developer ? '' : ' is-hidden'}`}
          aria-label="Answer mode"
          title={
            mode === 'agent'
              ? 'Agent: searches, searches again with different words when unsure, asks when your question is unclear, and checks every quote. Slower, more careful.'
              : 'Quick: searches once and answers once, with the same quote check. Faster, and the simple version the agent is compared against.'
          }
          aria-hidden={!developer}
        >
          <button
            className={mode === 'agent' ? 'active' : ''}
            tabIndex={developer ? 0 : -1}
            type="button"
            onClick={() => onModeChange('agent')}
          >
            Agent
          </button>
          <button
            className={mode === 'baseline' ? 'active' : ''}
            tabIndex={developer ? 0 : -1}
            type="button"
            onClick={() => onModeChange('baseline')}
          >
            Quick
          </button>
        </div>
      </div>
      <p
        className={`mode-hint${developer ? '' : ' is-hidden'}`}
        aria-hidden={!developer}
      >
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

      <div className="messages" aria-live="polite">
        {messages.length === 0 && (
          <div className="welcome-state">
            <div className="welcome-row">
              <PolicyPilotMark className="welcome-mark" />
              <h3>
                {personalizedGreeting(firstName)}. What would you like to know?
              </h3>
            </div>
          </div>
        )}

        {messages.map((message, index) => {
          const archivedClarification =
            message.role === 'assistant' &&
            message.answer?.clarification &&
            lastClarification?.id !== message.id
          const clarificationReply = isClarificationReply(messages, index)

          return (
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
                {message.role === 'assistant' ? (
                  <PolicyPilotMark />
                ) : (
                  <UserAvatar />
                )}
              </div>
              <div className="message-content">
                <span className="message-author">
                  {message.role === 'assistant' ? 'PolicyPilot' : 'You'}
                </span>
                {clarificationReply && (
                  <span className="clarification-response-label">
                    Selected clarification response
                  </span>
                )}
                {message.meta && (
                  <span className="message-meta">{message.meta}</span>
                )}
                {message.text && <p>{message.text}</p>}
                {archivedClarification && (
                  <div className="clarification-record">
                    <span>Clarification asked</span>
                    <p>{message.answer?.clarification?.prompt}</p>
                  </div>
                )}
                {message.answer && (
                  <AnswerView
                    answer={message.answer}
                    onCitationOpen={onCitationOpen}
                  />
                )}
                {message.role === 'assistant' && message.answer && (
                  <div className="message-tools">
                    <CopyButton answer={message.answer} />
                  </div>
                )}
              </div>
            </article>
          )
        })}

        {!busy && lastAnswerHasSources(messages) && (
          <div className="followups" aria-label="Suggested follow-up questions">
            {followUps.map((text) => (
              <button key={text} type="button" onClick={() => onSend(text)}>
                {text}
              </button>
            ))}
          </div>
        )}

        {busy && (
          <article className="message message-assistant working-message">
            <div className="assistant-avatar" aria-hidden="true">
              <AnimatedMark speed={1.4} />
            </div>
            <div className="message-content">
              <span className="message-author">PolicyPilot</span>
              <p className="working-line answer-bubble">
                <span className="thinking-dots">
                  <i />
                  <i />
                  <i />
                </span>
                <span className="working-text">
                  {streamLabel ?? 'Looking through the documents…'}
                </span>
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
            rows={1}
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
        {messages.length === 0 && (
          <div className="suggestions" aria-label="Suggested questions">
            {examples.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => {
                  setContent(example)
                  inputRef.current?.focus()
                }}
              >
                {example}
              </button>
            ))}
          </div>
        )}
        <p>
          Sample policies, not official NYU policy. Check the cited page before
          relying on an answer.
        </p>
      </div>
    </section>
  )
}
