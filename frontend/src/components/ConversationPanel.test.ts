import { describe, expect, it } from 'vitest'
import type { DisplayMessage } from './ConversationPanel'
import { latestPendingClarification } from './conversationState'

const clarification: DisplayMessage = {
  id: 'clarification',
  role: 'assistant',
  answer: {
    paragraphs: [],
    claims: [],
    citations: [],
    notices: [],
    clarification: {
      prompt: 'Which account type?',
      options: ['Student', 'Faculty'],
    },
  },
}

describe('latestPendingClarification', () => {
  it('shows the clarification when it is the newest assistant message', () => {
    expect(latestPendingClarification([clarification])).toBe(clarification)
  })

  it('hides a clarification after its reply has received an answer', () => {
    const reply: DisplayMessage = { id: 'reply', role: 'user', text: 'Student' }
    const answer: DisplayMessage = {
      id: 'answer',
      role: 'assistant',
      answer: {
        paragraphs: ['Renewed automatically.'],
        claims: [],
        citations: [],
        notices: [],
      },
    }
    expect(
      latestPendingClarification([clarification, reply, answer]),
    ).toBeNull()
  })
})
