import type { AnswerPayload } from './types'

/** What the chat shows when a turn fails: a short, human sentence instead of silence. */
export function failureAnswer(existing?: AnswerPayload | null): AnswerPayload {
  const useful = existing && existing.paragraphs.some((text) => text.trim())
  return {
    paragraphs: useful
      ? existing.paragraphs
      : [
          'Sorry, I could not finish that one. Please try again, or ask it a little differently.',
        ],
    claims: [],
    citations: existing?.citations ?? [],
    notices: [
      { type: 'partial', message: 'This question did not complete.' },
      ...(existing?.notices ?? []),
    ],
    clarification: null,
  }
}
