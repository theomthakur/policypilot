import { createServer } from 'node:http'
import { randomUUID } from 'node:crypto'

const port = Number(process.env.PORT ?? 4010)
const documents = [
  {
    id: 'doc-mfa',
    title: 'Identity and Multi-Factor Authentication Standard',
    filename: 'identity-and-mfa.pdf',
    page_count: 8,
    status: 'ready',
    source: 'bundled',
  },
  {
    id: 'doc-remote',
    title: 'Remote Access and VPN Policy',
    filename: 'remote-access.pdf',
    page_count: 6,
    status: 'ready',
    source: 'bundled',
  },
  {
    id: 'doc-data',
    title: 'Research Data Classification and Storage',
    filename: 'research-data.pdf',
    page_count: 10,
    status: 'ready',
    source: 'bundled',
  },
]
const ingestionRuns = new Map()
const sessions = new Map()
const turns = new Map()

function json(response, status, body) {
  response.writeHead(status, {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-store',
  })
  response.end(JSON.stringify(body))
}

async function readJson(request) {
  const parts = []
  for await (const part of request) parts.push(part)
  return parts.length ? JSON.parse(Buffer.concat(parts).toString('utf8')) : {}
}

function citation(id, number, documentId, documentTitle, page, quote) {
  return {
    id,
    number,
    document_id: documentId,
    document_title: documentTitle,
    page,
    quote,
    validation_status: 'verified',
  }
}

function answerFor(content) {
  const lower = content.toLowerCase()
  if (lower.includes('how long can i keep it')) {
    return {
      paragraphs: [
        'The applicable retention period depends on what “it” refers to.',
      ],
      claims: [],
      citations: [],
      notices: [],
      clarification: {
        prompt: 'Which type of information or system are you asking about?',
        options: [
          'Restricted research data',
          'Account records',
          'Security logs',
        ],
      },
    }
  }

  const mfaQuote =
    'Remote access to research systems requires multi-factor authentication for every interactive session.'
  const vpnQuote =
    'Researchers must connect through the approved university VPN before accessing restricted services from off campus.'
  const citations = [
    citation(
      'cite-mfa',
      1,
      'doc-mfa',
      'Identity and Multi-Factor Authentication Standard',
      4,
      mfaQuote,
    ),
    citation(
      'cite-remote',
      2,
      'doc-remote',
      'Remote Access and VPN Policy',
      3,
      vpnQuote,
    ),
  ]
  return {
    paragraphs: [
      'Remote research access requires multi-factor authentication on every interactive session and an approved university VPN connection before restricted services are accessed off campus.',
      'These requirements apply together: the VPN establishes the approved network path, while MFA verifies the person initiating the session.',
    ],
    claims: [
      {
        id: 'claim-1',
        text: 'MFA is required for each remote interactive session.',
        citation_ids: ['cite-mfa'],
      },
      {
        id: 'claim-2',
        text: 'The approved VPN is required off campus.',
        citation_ids: ['cite-remote'],
      },
    ],
    citations,
    notices: lower.includes('conflict')
      ? [
          {
            type: 'conflict',
            message:
              'An older bulletin differs from the current standard; both sources should be reviewed.',
          },
        ]
      : [],
    clarification: null,
  }
}

function eventsFor(turnId, content) {
  const answer = answerFor(content)
  const totals = {
    steps: 5,
    tool_calls: 3,
    prompt_tokens: 1240,
    completion_tokens: 286,
    estimated_cost_usd: 0.0018,
    latency_ms: 2380,
    stop_reason: answer.clarification
      ? 'clarification_requested'
      : 'answer_complete',
  }
  const now = new Date().toISOString()
  const events = [
    {
      id: `${turnId}-1`,
      sequence: 1,
      type: 'turn_started',
      timestamp: now,
      status: 'ok',
      summary: 'Question accepted and bounded execution started.',
      duration_ms: 4,
    },
    {
      id: `${turnId}-2`,
      sequence: 2,
      type: 'tool_call',
      timestamp: now,
      status: 'ok',
      summary: 'Searching for the user’s original terminology.',
      tool_name: 'search_documents',
      input: { query: content, top_k: 6 },
      duration_ms: 310,
    },
    {
      id: `${turnId}-3`,
      sequence: 3,
      type: 'tool_result',
      timestamp: now,
      status: 'empty',
      summary:
        'The first search had weak coverage; one potentially relevant page was found.',
      tool_name: 'search_documents',
      result: {
        hit_count: 1,
        documents: [
          {
            id: 'doc-remote',
            title: 'Remote Access and VPN Policy',
            pages: [3],
          },
        ],
      },
      duration_ms: 184,
    },
    {
      id: `${turnId}-4`,
      sequence: 4,
      type: 'query_revised',
      timestamp: now,
      status: 'ok',
      summary: 'Revised the query using policy terms found in the corpus.',
      input: {
        query: 'remote research access VPN multi-factor authentication',
      },
      duration_ms: 12,
    },
    {
      id: `${turnId}-5`,
      sequence: 5,
      type: 'tool_result',
      timestamp: now,
      status: 'ok',
      summary:
        'Found supporting passages in two documents and inspected their pages.',
      tool_name: 'read_document_pages',
      result: {
        hit_count: 2,
        documents: [
          {
            id: 'doc-mfa',
            title: 'Identity and Multi-Factor Authentication Standard',
            pages: [4],
          },
          {
            id: 'doc-remote',
            title: 'Remote Access and VPN Policy',
            pages: [3],
          },
        ],
      },
      duration_ms: 442,
    },
    {
      id: `${turnId}-6`,
      sequence: 6,
      type: answer.clarification ? 'clarification' : 'answer',
      timestamp: now,
      status: 'ok',
      summary: answer.clarification
        ? 'A targeted clarification is required before retrieval can continue.'
        : 'Answer completed with two verified page citations.',
      answer,
      totals,
      duration_ms: 1428,
      prompt_tokens: 1240,
      completion_tokens: 286,
    },
  ]
  return { events, answer, totals }
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? '/', `http://${request.headers.host}`)
  const path = url.pathname

  if (request.method === 'GET' && path === '/api/v1/health/ready') {
    return json(response, 200, {
      status: process.env.REDIS_DOWN ? 'degraded' : 'ok',
      checks: {
        postgres: { status: 'ok' },
        redis: {
          status: process.env.REDIS_DOWN ? 'degraded' : 'ok',
          message: process.env.REDIS_DOWN
            ? 'Search cache unavailable'
            : undefined,
        },
      },
      version: 'mock-0.1.0',
    })
  }
  if (request.method === 'GET' && path === '/api/v1/documents')
    return json(response, 200, { items: documents })
  if (request.method === 'POST' && path === '/api/v1/documents') {
    for await (const _part of request) {
      /* consume multipart body */
    }
    const id = randomUUID()
    const runId = randomUUID()
    const document = {
      id,
      title: 'Uploaded policy',
      filename: 'uploaded-policy.pdf',
      page_count: 5,
      status: 'embedding',
      source: 'uploaded',
    }
    const run = {
      id: runId,
      status: 'embedding',
      stage: 'Creating searchable chunks',
      progress: 70,
    }
    documents.push(document)
    ingestionRuns.set(runId, run)
    setTimeout(() => {
      document.status = 'ready'
      ingestionRuns.set(runId, {
        ...run,
        status: 'ready',
        stage: 'Ready',
        progress: 100,
      })
    }, 1200)
    return json(response, 202, { document, ingestion_run: run })
  }
  const ingestionMatch = path.match(/^\/api\/v1\/ingestion\/([^/]+)$/)
  if (request.method === 'GET' && ingestionMatch) {
    const run = ingestionRuns.get(ingestionMatch[1])
    return run
      ? json(response, 200, run)
      : json(response, 404, {
          error: {
            code: 'NOT_FOUND',
            message: 'Ingestion run not found.',
            details: {},
          },
        })
  }
  if (request.method === 'POST' && path === '/api/v1/sessions') {
    const sessionId = randomUUID()
    sessions.set(sessionId, { id: sessionId, turns: [] })
    return json(response, 201, { session_id: sessionId })
  }
  const sessionMatch = path.match(/^\/api\/v1\/sessions\/([^/]+)$/)
  if (request.method === 'GET' && sessionMatch) {
    const session = sessions.get(sessionMatch[1])
    return session
      ? json(response, 200, session)
      : json(response, 404, {
          error: {
            code: 'SESSION_NOT_FOUND',
            message: 'Session not found.',
            details: {},
          },
        })
  }
  const messageMatch = path.match(/^\/api\/v1\/sessions\/([^/]+)\/messages$/)
  if (request.method === 'POST' && messageMatch) {
    const body = await readJson(request)
    const session = sessions.get(messageMatch[1])
    if (!session)
      return json(response, 404, {
        error: {
          code: 'SESSION_NOT_FOUND',
          message: 'Session not found.',
          details: {},
        },
      })
    const turnId = randomUUID()
    session.turns.push({
      id: randomUUID(),
      role: 'user',
      content: body.content,
      created_at: new Date().toISOString(),
    })
    const generated = eventsFor(turnId, body.content)
    turns.set(turnId, {
      id: turnId,
      status: 'running',
      stop_reason: null,
      answer: null,
      trace: [],
      totals: null,
      generated,
    })
    return json(response, 202, { turn_id: turnId })
  }
  const eventsMatch = path.match(/^\/api\/v1\/turns\/([^/]+)\/events$/)
  if (request.method === 'GET' && eventsMatch) {
    const turn = turns.get(eventsMatch[1])
    if (!turn)
      return json(response, 404, {
        error: {
          code: 'TURN_NOT_FOUND',
          message: 'Turn not found.',
          details: {},
        },
      })
    response.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    })
    let index = 0
    const timer = setInterval(() => {
      const event = turn.generated.events[index]
      if (!event) {
        clearInterval(timer)
        response.end()
        return
      }
      turn.trace.push(event)
      response.write(`data: ${JSON.stringify(event)}\n\n`)
      index += 1
      if (event.type === 'answer' || event.type === 'clarification') {
        turn.status = 'completed'
        turn.stop_reason = event.totals.stop_reason
        turn.answer = event.answer
        turn.totals = event.totals
        clearInterval(timer)
        response.end()
      }
    }, 260)
    request.on('close', () => clearInterval(timer))
    return
  }
  const turnMatch = path.match(/^\/api\/v1\/turns\/([^/]+)$/)
  if (request.method === 'GET' && turnMatch) {
    const turn = turns.get(turnMatch[1])
    return turn
      ? json(response, 200, {
          id: turn.id,
          status: turn.status,
          stop_reason: turn.stop_reason,
          answer: turn.answer,
          trace: turn.trace,
          totals: turn.totals,
        })
      : json(response, 404, {
          error: {
            code: 'TURN_NOT_FOUND',
            message: 'Turn not found.',
            details: {},
          },
        })
  }
  const pageMatch = path.match(/^\/api\/v1\/documents\/([^/]+)\/pages\/(\d+)$/)
  if (request.method === 'GET' && pageMatch) {
    const [, documentId, pageValue] = pageMatch
    const page = Number(pageValue)
    const title =
      documents.find((document) => document.id === documentId)?.title ??
      'Policy document'
    const text =
      documentId === 'doc-mfa'
        ? 'Identity and access requirements\n\nRemote access to research systems requires multi-factor authentication for every interactive session. Service accounts follow the separately documented non-interactive credential standard.'
        : 'Remote connectivity\n\nResearchers must connect through the approved university VPN before accessing restricted services from off campus. The VPN client must remain active for the duration of access.'
    return json(response, 200, {
      document_id: documentId,
      document_title: title,
      page,
      text,
    })
  }

  return json(response, 404, {
    error: {
      code: 'NOT_FOUND',
      message: 'Mock route not found.',
      details: { path },
    },
  })
})

server.listen(port, '127.0.0.1', () => {
  console.log(`PolicyPilot mock API listening on http://127.0.0.1:${port}`)
})
