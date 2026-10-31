import type { DisplayMessage } from './ConversationPanel'

export function latestPendingClarification(
  messages: DisplayMessage[],
): DisplayMessage | null {
  const last = messages.at(-1)
  return last?.role === 'assistant' && last.answer?.clarification ? last : null
}

export function isClarificationReply(
  messages: DisplayMessage[],
  index: number,
): boolean {
  const message = messages[index]
  const previous = messages[index - 1]
  return Boolean(message?.role === 'user' && previous?.answer?.clarification)
}
