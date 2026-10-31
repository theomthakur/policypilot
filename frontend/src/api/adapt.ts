// The backend contract (contracts/openapi.yaml) and the UI's view models differ in naming and shape.
// Everything that crosses the network goes through these pure functions, so components never see raw
// backend payloads.
import { humanizeEvent } from './humanize'
import type {
  AnswerPayload,
  Citation,
  HealthResponse,
  IngestionRun,
  PageResponse,
  PolicyDocument,
  RunTotals,
  ServiceStatus,
  TraceEvent,
  TraceEventType,
  TraceStatus,
  Turn,
  TurnStatus,
} from './types'

type Raw = Record<string, unknown>
type HumanRevision = {
  previous_query?: string
  new_query?: string
  reason?: string
}

const asRecord = (value: unknown): Raw =>
  value && typeof value === 'object' ? (value as Raw) : {}
const asString = (value: unknown, fallback = ''): string =>
  typeof value === 'string' ? value : fallback
const asNumber = (value: unknown, fallback = 0): number =>
  typeof value === 'number' ? value : fallback
const asArray = (value: unknown): Raw[] =>
  Array.isArray(value) ? value.map(asRecord) : []

export function adaptHealth(raw: Raw): HealthResponse {
  const checks: HealthResponse['checks'] = {}
  Object.entries(asRecord(raw.checks)).forEach(([name, value]) => {
    const status = asString(value)
    checks[name] = {
      status: (status === 'ok'
        ? 'ok'
        : status === 'missing' || status === 'pending'
          ? 'degraded'
          : 'down') as ServiceStatus,
      message: status === 'ok' ? undefined : status,
    }
  })
  return {
    status: asString(raw.status, 'down') as ServiceStatus,
    version: asString(raw.version),
    checks,
  }
}

const documentStatus: Record<string, PolicyDocument['status']> = {
  queued: 'pending',
  processing: 'extracting',
  ready: 'ready',
  failed: 'failed',
}

export function adaptDocument(raw: Raw): PolicyDocument {
  return {
    id: asString(raw.id),
    title: asString(raw.title),
    filename: asString(raw.filename),
    page_count: asNumber(raw.page_count),
    status: documentStatus[asString(raw.status)] ?? 'pending',
    source:
      raw.source === 'corpus'
        ? 'bundled'
        : raw.source === 'reference'
          ? 'reference'
          : 'uploaded',
    error: (raw.error as string | null | undefined) ?? null,
  }
}

const stageStatus: Record<string, IngestionRun['status']> = {
  queued: 'pending',
  parsing: 'extracting',
  chunking: 'extracting',
  embedding: 'embedding',
  indexing: 'embedding',
  done: 'ready',
  failed: 'failed',
}

export function adaptIngestion(raw: Raw): IngestionRun {
  const total = asNumber(raw.page_count)
  const done = asNumber(raw.pages_done)
  const stage = asString(raw.stage, 'queued')
  const finished = raw.status === 'succeeded'
  return {
    id: asString(raw.id),
    status: finished ? 'ready' : (stageStatus[stage] ?? 'pending'),
    stage,
    error: (raw.error as string | null | undefined) ?? null,
    progress: finished ? 1 : total > 0 ? done / total : 0,
  }
}

export function adaptUpload(raw: Raw): {
  document: PolicyDocument
  ingestion_run: IngestionRun
  duplicate: boolean
} {
  return {
    document: adaptDocument(asRecord(raw.document)),
    ingestion_run: adaptIngestion(asRecord(raw.ingestion_run)),
    duplicate: raw.duplicate === true,
  }
}

export function adaptPage(raw: Raw): PageResponse {
  return {
    document_id: asString(raw.document_id),
    document_title: asString(raw.title) || undefined,
    page: asNumber(raw.page),
    text: asString(raw.text),
  }
}

export function adaptAnswer(
  rawAnswer: unknown,
  rawClarification: unknown,
): AnswerPayload | null {
  const clarification = asRecord(rawClarification)
  if (asString(clarification.question)) {
    return {
      paragraphs: [],
      claims: [],
      citations: [],
      notices: [],
      clarification: {
        prompt: asString(clarification.question),
        options: Array.isArray(clarification.options)
          ? clarification.options.map(String)
          : [],
      },
    }
  }
  if (!rawAnswer) return null
  const answer = asRecord(rawAnswer)
  const citations: Citation[] = asArray(answer.citations).map((item) => ({
    id: String(item.index),
    number: asNumber(item.index),
    document_id: asString(item.document_id),
    document_title: asString(item.title),
    page: asNumber(item.page),
    quote: asString(item.quote),
    validation_status: item.verified ? 'verified' : 'unverified',
  }))
  return {
    paragraphs: [asString(answer.summary)].filter(Boolean),
    claims: asArray(answer.claims).map((claim, index) => ({
      id: `claim-${index + 1}`,
      text: asString(claim.text),
      citation_ids: Array.isArray(claim.citation_indexes)
        ? claim.citation_indexes.map(String)
        : [],
    })),
    citations,
    notices: asArray(answer.notices).map((notice) => ({
      type:
        asString(notice.kind) === 'assumption'
          ? 'warning'
          : asNoticeType(notice.kind),
      message: asString(notice.text),
    })),
    clarification: null,
  }
}

function asNoticeType(
  kind: unknown,
): 'conflict' | 'missing_evidence' | 'partial' {
  return kind === 'conflict' || kind === 'missing_evidence' ? kind : 'partial'
}

export function adaptTotals(
  raw: unknown,
  stopReason: unknown,
): RunTotals | null {
  const totals = asRecord(raw)
  if (Object.keys(totals).length === 0) return null
  return {
    steps: asNumber(totals.steps),
    tool_calls: asNumber(totals.tool_calls),
    tool_attempts: asNumber(totals.tool_attempts),
    blocked_calls: asNumber(totals.blocked_calls),
    model_requests: asNumber(totals.model_requests),
    prompt_tokens: asNumber(totals.prompt_tokens),
    completion_tokens: asNumber(totals.completion_tokens),
    estimated_cost_usd: asNumber(totals.estimated_cost_usd),
    latency_ms: asNumber(totals.latency_ms),
    stop_reason: asString(stopReason, 'unknown'),
  }
}

const eventTypes: Record<string, TraceEventType> = {
  evaluate: 'evidence_assessment',
  assessment: 'evidence_assessment',
  clarification_requested: 'clarification',
}

const eventStatus: Record<string, TraceStatus> = {
  weak: 'empty',
  info: 'ok',
}

export function adaptEvent(raw: Raw): TraceEvent {
  const backendType = asString(raw.type)
  const status = asString(raw.status, 'ok')
  const result = asRecord(raw.result)
  const pages = asArray(result.pages)
  const documents = new Map<
    string,
    { id: string; title: string; pages: number[] }
  >()
  pages.forEach((page) => {
    const id = asString(page.document_id)
    const entry = documents.get(id) ?? {
      id,
      title: asString(page.title),
      pages: [],
    }
    entry.pages.push(asNumber(page.page))
    documents.set(id, entry)
  })
  const tokens = asRecord(raw.tokens)
  const technical = asString(raw.summary)
  const type: TraceEventType =
    backendType === 'tool_result' && status === 'retried'
      ? 'retry'
      : ((eventTypes[backendType] ?? backendType) as TraceEventType)
  const human = humanizeEvent({
    type: backendType,
    status,
    tool: (raw.tool as string | null | undefined) ?? null,
    input: (raw.input as Record<string, unknown> | null | undefined) ?? null,
    summary: technical,
    hits: typeof result.hits === 'number' ? result.hits : undefined,
    weak: Boolean(result.weak),
    errorCode: asString(result.error_code) || undefined,
    revision: (raw.revision as HumanRevision | null | undefined) ?? null,
    scope: (raw.scope as string | null | undefined) ?? null,
    subQuestions: Array.isArray(raw.sub_questions)
      ? raw.sub_questions.map(String)
      : undefined,
    limitName: asString(asRecord(raw.limit).name) || undefined,
  })
  return {
    id: `${asString(raw.turn_id)}-${asNumber(raw.seq)}`,
    sequence: asNumber(raw.seq),
    type,
    timestamp: asString(raw.ts),
    status: eventStatus[status] ?? (status as TraceStatus),
    summary: human.text,
    title: human.title,
    hidden: human.hidden,
    technical_summary: technical,
    tool_name: (raw.tool as string | null | undefined) ?? null,
    input: (raw.input as Record<string, unknown> | null | undefined) ?? null,
    result:
      Object.keys(result).length > 0
        ? {
            hit_count: asNumber(result.hits, undefined as unknown as number),
            documents: [...documents.values()],
            message: asString(result.error_code) || undefined,
          }
        : null,
    duration_ms: (raw.duration_ms as number | undefined) ?? null,
    prompt_tokens: tokens.prompt == null ? null : asNumber(tokens.prompt),
    completion_tokens:
      tokens.completion == null ? null : asNumber(tokens.completion),
  }
}

export function adaptTurn(raw: Raw): Turn {
  const status = asString(raw.status, 'running')
  return {
    id: asString(raw.id),
    status: (['running', 'completed', 'failed'].includes(status)
      ? status
      : 'running') as TurnStatus,
    stop_reason: (raw.stop_reason as string | null | undefined) ?? null,
    answer: adaptAnswer(raw.answer, raw.clarification),
    trace: asArray(raw.events).map(adaptEvent),
    totals: adaptTotals(raw.totals, raw.stop_reason),
  }
}
