import type {
  ApiErrorBody,
  HealthResponse,
  IngestionRun,
  PageResponse,
  PolicyDocument,
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
  healthReady: () => request<HealthResponse>('/health/ready'),
  listDocuments: async () => {
    const response = await request<{ items: PolicyDocument[] }>('/documents')
    return response.items
  },
  getIngestion: (runId: string) => request<IngestionRun>(`/ingestion/${runId}`),
  createSession: () =>
    request<{ session_id: string }>('/sessions', { method: 'POST' }),
  getSession: (sessionId: string) =>
    request<SessionResponse>(`/sessions/${sessionId}`),
  sendMessage: (
    sessionId: string,
    content: string,
    mode: 'agent' | 'baseline',
  ) =>
    request<{ turn_id: string }>(`/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content, mode }),
    }),
  getTurn: (turnId: string) => request<Turn>(`/turns/${turnId}`),
  getPage: (documentId: string, page: number) =>
    request<PageResponse>(`/documents/${documentId}/pages/${page}`),
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
        resolve(JSON.parse(xhr.responseText) as UploadResponse)
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
