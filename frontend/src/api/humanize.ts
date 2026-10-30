// Plain-English wording for the execution trace and the run summary. The backend sends precise,
// production-style events; this turns each one into a sentence a person can read.

export interface HumanInput {
  type: string
  status: string
  tool?: string | null
  input?: Record<string, unknown> | null
  summary: string
  hits?: number
  weak?: boolean
  errorCode?: string
  revision?: {
    previous_query?: string
    new_query?: string
    reason?: string
  } | null
  subQuestions?: string[]
  limitName?: string
}

export interface HumanEvent {
  title: string
  text: string
  hidden: boolean
}

const quote = (value: unknown) => `“${String(value ?? '').trim()}”`

const limitText: Record<string, string> = {
  steps: 'Used all the allowed steps.',
  tool_calls: 'Used all the allowed searches.',
  time: 'Ran out of time.',
  tokens: 'Used all the allowed reading budget.',
  budget: "Today's demo budget is used up.",
}

export function humanizeEvent(e: HumanInput): HumanEvent {
  const say = (title: string, text: string): HumanEvent => ({
    title,
    text,
    hidden: false,
  })
  switch (e.type) {
    case 'turn_started':
    case 'turn_completed':
    case 'evaluate':
      return { title: '', text: '', hidden: true }
    case 'plan':
      return say(
        'Planning',
        e.subQuestions && e.subQuestions.length > 0
          ? `Working out: ${e.subQuestions.join('; ')}`
          : 'Working out what to look for.',
      )
    case 'tool_call': {
      if (e.status === 'blocked') {
        return say(
          'Skipped',
          /revision/i.test(e.summary)
            ? 'Skipped a search: it had already tried different wording too many times.'
            : 'Skipped a search that repeated an earlier one.',
        )
      }
      if (e.tool === 'search_documents') {
        return say(
          'Searching',
          `Looking for ${quote(e.input?.query)} across the documents.`,
        )
      }
      if (e.tool === 'list_documents') {
        return say(
          'Checking the library',
          'Seeing which documents are available.',
        )
      }
      if (e.tool === 'read_document_pages') {
        const first = e.input?.page_start
        const last = e.input?.page_end
        const range =
          first && last && first !== last
            ? `pages ${first} to ${last}`
            : first
              ? `page ${first}`
              : 'a page'
        return say('Reading', `Reading ${range} of a document in full.`)
      }
      if (e.tool === 'get_document_outline') {
        return say('Looking at structure', "Checking a document's headings.")
      }
      return say('Working', e.summary)
    }
    case 'tool_result': {
      if (e.status === 'retried')
        return say(
          'Trying once more',
          'That step failed, so it is being tried again.',
        )
      if (e.status === 'error') {
        return say(
          'Hit a problem',
          e.errorCode === 'TIMEOUT'
            ? 'A step took too long.'
            : e.errorCode === 'INVALID_ARGUMENT' ||
                /INVALID_ARGUMENT/.test(e.summary)
              ? 'The request was malformed, so it is being corrected.'
              : 'A step failed.',
        )
      }
      if (e.tool === 'search_documents') {
        const hits = e.hits ?? 0
        if (e.status === 'empty' || hits === 0)
          return say('Found nothing', 'No passage matched.')
        return say(
          'Found passages',
          `Found ${hits} passage${hits === 1 ? '' : 's'}${e.weak ? ', but none looked convincing' : ''}.`,
        )
      }
      if (e.tool === 'list_documents') return say('Library checked', e.summary)
      if (e.tool === 'read_document_pages')
        return say('Page read', 'Read the full text of the page.')
      return say('Done', e.summary)
    }
    case 'query_revised':
      return say(
        'Trying different words',
        e.revision?.new_query
          ? `Searching again for ${quote(e.revision.new_query)} ${
              e.revision.reason === 'uncovered_sub_question'
                ? 'because the first results did not cover everything.'
                : 'because the first results were not convincing.'
            }`
          : 'Searching again with different words.',
      )
    case 'clarification_requested':
      return say('Needs a detail from you', e.summary)
    case 'synthesize':
      return say(
        'Writing the answer',
        'Drafting an answer from the evidence found.',
      )
    case 'verify':
      return say(
        'Checking quotes',
        e.status === 'weak' || e.status === 'empty'
          ? 'Some quotes did not match their pages, so they are being fixed or removed.'
          : 'Every quote was found word for word on its page.',
      )
    case 'answer':
      return say('Answer ready', 'The answer is complete.')
    case 'limit_reached':
      return say(
        'Stopped early',
        `${limitText[e.limitName ?? ''] ?? 'A limit was reached.'} Giving what was found so far.`,
      )
    case 'injection_flagged':
      return say(
        'Ignored an instruction',
        'A document contained text trying to give orders. It was treated as plain text and not followed.',
      )
    default:
      return say(e.type.replaceAll('_', ' '), e.summary)
  }
}

const stopLabels: Record<string, string> = {
  answered: 'Answered',
  insufficient_evidence: 'Not in the documents',
  clarification_needed: 'Needs your input',
  limit_steps: 'Ran out of steps',
  limit_tool_calls: 'Ran out of searches',
  limit_time: 'Ran out of time',
  limit_tokens: 'Ran out of room',
  budget_exhausted: 'Daily budget used',
  tool_failure: 'A step failed',
  error: 'Something went wrong',
}

export function stopReasonLabel(reason: string): string {
  return stopLabels[reason] ?? reason.replaceAll('_', ' ')
}

export function eventStatusLabel(status: string): string {
  return (
    {
      ok: 'done',
      empty: 'nothing found',
      error: 'problem',
      retried: 'retrying',
      blocked: 'skipped',
      running: 'working',
    }[status] ?? status
  )
}
