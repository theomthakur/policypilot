import type { DisplayMessage } from './ConversationPanel'

export function latestPendingClarification(
  messages: DisplayMessage[],
): DisplayMessage | null {
  const last = messages.at(-1)
  return last?.role === 'assistant' && last.answer?.clarification ? last : null
}
