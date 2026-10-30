export type ServiceStatus = 'ok' | 'degraded' | 'down'
export type DocumentStatus =
  | 'pending'
  | 'extracting'
  | 'embedding'
  | 'ready'
  | 'failed'
export type TurnStatus = 'queued' | 'running' | 'completed' | 'failed'
export type TraceStatus =
  | 'running'
  | 'ok'
  | 'empty'
  | 'error'
  | 'retried'
  | 'blocked'
export type AnswerNoticeType =
  | 'conflict'
  | 'missing_evidence'
  | 'partial'
  | 'warning'

export interface HealthResponse {
  status: ServiceStatus
  checks: Record<string, { status: ServiceStatus; message?: string }>
  version: string
}

export interface PolicyDocument {
  id: string
  title: string
  filename: string
  page_count: number
  status: DocumentStatus
  source: 'bundled' | 'reference' | 'uploaded'
  error?: string | null
}

export interface IngestionRun {
  id: string
  status: DocumentStatus
  stage: string
  error?: string | null
  progress?: number
}

export interface UploadResponse {
  document: PolicyDocument
  ingestion_run: IngestionRun
}

export interface Citation {
  id: string
  number: number
  document_id: string
  document_title: string
  page: number
  quote: string
  validation_status: 'verified' | 'unsupported' | 'unverified'
}

export interface AnswerClaim {
  id: string
  text: string
  citation_ids: string[]
}

export interface AnswerNotice {
  type: AnswerNoticeType
  message: string
}

export interface Clarification {
  prompt: string
  options?: string[]
}

export interface AnswerPayload {
  paragraphs: string[]
  claims: AnswerClaim[]
  citations: Citation[]
  notices: AnswerNotice[]
  clarification?: Clarification | null
}

export interface RunTotals {
  steps: number
  tool_calls: number
  tool_attempts?: number
  blocked_calls?: number
  model_requests?: number
  prompt_tokens: number
  completion_tokens: number
  estimated_cost_usd: number
  latency_ms: number
  stop_reason: string
}

export type TraceEventType =
  | 'turn_started'
  | 'plan'
  | 'tool_call'
  | 'tool_result'
  | 'evidence_assessment'
  | 'query_revised'
  | 'retry'
  | 'timeout'
  | 'injection_flagged'
  | 'limit_reached'
  | 'clarification'
  | 'synthesize'
  | 'verify'
  | 'turn_completed'
  | 'answer'
  | 'turn_failed'

export interface TraceEvent {
  id: string
  sequence: number
  type: TraceEventType
  timestamp: string
  status: TraceStatus
  summary: string
  title?: string
  hidden?: boolean
  technical_summary?: string
  tool_name?: string | null
  input?: Record<string, unknown> | null
  result?: {
    hit_count?: number
    documents?: Array<{ id: string; title: string; pages: number[] }>
    message?: string
  } | null
  duration_ms?: number | null
  prompt_tokens?: number | null
  completion_tokens?: number | null
  answer?: AnswerPayload | null
  totals?: RunTotals | null
}

export interface Turn {
  id: string
  status: TurnStatus
  stop_reason?: string | null
  answer?: AnswerPayload | null
  trace: TraceEvent[]
  totals?: RunTotals | null
}

export interface SessionTurn {
  id: string
  role: 'user' | 'assistant'
  content: string
  answer?: AnswerPayload | null
  created_at: string
}

export interface SessionResponse {
  id: string
  turns: SessionTurn[]
}

export interface PageResponse {
  document_id: string
  document_title?: string
  page: number
  text: string
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    details?: Record<string, unknown>
  }
}

export interface RunConfiguration {
  model: {
    provider: string
    name: string
    temperature: number
    seed: number | null
    prompt_version: string
  }
  retrieval: {
    embedding_model: string
    embedding_dim: number
    chunk_tokens: number
    chunk_overlap_tokens: number
    candidates_per_retriever: number
    fusion: string
    default_top_k: number
  }
  agent_limits: {
    max_steps: number
    max_tool_calls: number
    max_query_revisions: number
    max_tool_retries: number
    tool_timeout_seconds: number
    turn_timeout_seconds: number
    max_tokens_per_turn: number
    max_pages_per_read: number
  }
  protections: {
    passcode_required: boolean
    rate_limit_per_minute: number
    daily_budget_usd: number
    upload_max_mb: number
    upload_max_pages: number
  }
}
