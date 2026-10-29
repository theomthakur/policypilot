import { useState } from 'react'
import type { Clarification } from '../api/types'

interface ClarificationCardProps {
  clarification: Clarification
  disabled?: boolean
  onReply: (reply: string) => void
}

export function ClarificationCard({
  clarification,
  disabled,
  onReply,
}: ClarificationCardProps) {
  const [reply, setReply] = useState('')

  return (
    <section
      className="clarification-card"
      aria-labelledby="clarification-title"
    >
      <div className="clarification-icon" aria-hidden="true">
        ?
      </div>
      <div className="clarification-content">
        <p className="eyebrow">Clarification needed</p>
        <h3 id="clarification-title">{clarification.prompt}</h3>
        {clarification.options && clarification.options.length > 0 && (
          <div className="option-list" aria-label="Suggested replies">
            {clarification.options.map((option) => (
              <button
                key={option}
                type="button"
                disabled={disabled}
                onClick={() => onReply(option)}
              >
                {option}
              </button>
            ))}
          </div>
        )}
        <form
          className="clarification-form"
          onSubmit={(event) => {
            event.preventDefault()
            const value = reply.trim()
            if (!value) return
            onReply(value)
            setReply('')
          }}
        >
          <label className="visually-hidden" htmlFor="clarification-reply">
            Write another reply
          </label>
          <input
            id="clarification-reply"
            value={reply}
            disabled={disabled}
            onChange={(event) => setReply(event.target.value)}
            placeholder="Or type your answer…"
          />
          <button
            type="submit"
            disabled={disabled || reply.trim().length === 0}
          >
            Send
          </button>
        </form>
      </div>
    </section>
  )
}
