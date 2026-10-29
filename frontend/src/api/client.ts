import {
  adaptDocument,
  adaptHealth,
  adaptIngestion,
  adaptPage,
  adaptTurn,
  adaptUpload,
} from './adapt'
import type {
  ApiErrorBody,
  SessionResponse,
  Turn,
  UploadResponse,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'
const PASSCODE_KEY = 'policypilot_demo_passcode'

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function authHeaders(): HeadersInit {
  const passcode = sessionStorage.getItem(PASSCODE_KEY)
  return passcode ? { 'X-Demo-Passcode': passcode } : {}
}

async function parseError(response: Response): Promise<ApiError> {
  let body: ApiErrorBody | undefined
  try {
    body = (await response.json()) as ApiErrorBody
  } catch {
    // The proxy may return an HTML error page; keep the public message generic.
  }
  const error = body?.error
  return new ApiError(
    response.status,
    error?.code ?? `HTTP_${response.status}`,
    error?.message ?? 'The request could not be completed.',
    error?.details,
  )
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  Object.entries(authHeaders()).forEach(([key, value]) =>
    headers.set(key, value),
  )
  if (init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: 'same-origin',
  })

  if (!response.ok) {
    if (response.status === 401)
      window.dispatchEvent(new Event('policypilot:auth-required'))
    throw await parseError(response)
  }

  return (await response.json()) as T
}

export function setDemoPasscode(passcode: string): void {
  sessionStorage.setItem(PASSCODE_KEY, passcode)
}

export function clearDemoPasscode(): void {
  sessionStorage.removeItem(PASSCODE_KEY)
}

export const api = {
  healthReady: async () =>
    adaptHealth(await request<Record<string, unknown>>('/health/ready')),
  listDocuments: async () => {
    const response = await request<{ items: Record<string, unknown>[] }>(
      '/documents',
    )
    return response.items.map(adaptDocument)
  },
  getIngestion: async (runId: string) =>
    adaptIngestion(
      await request<Record<string, unknown>>(`/ingestion/${runId}`),
    ),
  createSession: () =>
    request<{ session_id: string }>('/sessions', { method: 'POST' }),
  getSession: async (sessionId: string): Promise<SessionResponse> => {
    const session = await request<{
      id: string
      turns: {
        id: string
        question: string
        status: string
        created_at: string
      }[]
    }>(`/sessions/${sessionId}`)
    const turns = await Promise.all(
      session.turns.map(async (item) => ({
        item,
        turn:
          item.status === 'running'
            ? null
            : adaptTurn(
                await request<Record<string, unknown>>(`/turns/${item.id}`),
              ),
      })),
    )
    return {
      id: session.id,
      turns: turns.flatMap(({ item, turn }) => [
        {
          id: `user-${item.id}`,
          role: 'user' as const,
          content: item.question,
          created_at: item.created_at,
        },
        ...(turn?.answer
          ? [
              {
                id: `assistant-${item.id}`,
                role: 'assistant' as const,
                content: '',
                answer: turn.answer,
                created_at: item.created_at,
              },
            ]
          : []),
      ]),
    }
  },
  sendMessage: (
    sessionId: string,
    content: string,
    mode: 'agent' | 'baseline',
    replyToClarification?: string | null,
  ) =>
    request<{ turn_id: string }>(`/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        content,
        mode,
        ...(replyToClarification
          ? { reply_to_clarification: replyToClarification }
          : {}),
      }),
    }),
  getTurn: async (turnId: string): Promise<Turn> =>
    adaptTurn(await request<Record<string, unknown>>(`/turns/${turnId}`)),
  getPage: async (documentId: string, page: number) =>
    adaptPage(
      await request<Record<string, unknown>>(
        `/documents/${documentId}/pages/${page}`,
      ),
    ),
}

export function uploadDocument(
  file: File,
  onProgress: (percent: number) => void,
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE}/documents`)
    xhr.withCredentials = true
    const passcode = sessionStorage.getItem(PASSCODE_KEY)
    if (passcode) xhr.setRequestHeader('X-Demo-Passcode', passcode)

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable)
        onProgress(Math.round((event.loaded / event.total) * 100))
    })
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(
          adaptUpload(JSON.parse(xhr.responseText) as Record<string, unknown>),
        )
        return
      }
      if (xhr.status === 401)
        window.dispatchEvent(new Event('policypilot:auth-required'))
      try {
        const body = JSON.parse(xhr.responseText) as ApiErrorBody
        reject(
          new ApiError(
            xhr.status,
            body.error.code,
            body.error.message,
            body.error.details,
          ),
        )
      } catch {
        reject(new ApiError(xhr.status, `HTTP_${xhr.status}`, 'Upload failed.'))
      }
    })
    xhr.addEventListener('error', () =>
      reject(new ApiError(0, 'NETWORK_ERROR', 'Upload failed.')),
    )

    const form = new FormData()
    form.append('file', file)
    xhr.send(form)
  })
}

export function turnEventsUrl(turnId: string): string {
  return `${API_BASE}/turns/${turnId}/events`
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong.'
}
