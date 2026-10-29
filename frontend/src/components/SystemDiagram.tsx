import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import './SystemDiagram.css'

interface NodeSpec {
  logos?: string[]
  name: string
  detail: string
}

interface Layer {
  number: string
  tone: 'client' | 'edge' | 'api' | 'agent' | 'data'
  title: string
  nodes: NodeSpec[]
}

const layers: Layer[] = [
  {
    number: '1',
    tone: 'client',
    title: 'Client',
    nodes: [
      {
        logos: ['react', 'vite'],
        name: 'React + TypeScript',
        detail:
          'Chat, verified-citation drawer, live execution trace (SSE), uploads, clarification card.',
      },
    ],
  },
  {
    number: '2',
    tone: 'edge',
    title: 'Edge',
    nodes: [
      {
        logos: ['caddy'],
        name: 'Caddy',
        detail: 'Automatic HTTPS in production.',
      },
      {
        logos: ['nginx'],
        name: 'nginx',
        detail:
          'Serves the app, proxies /api, keeps the event stream unbuffered.',
      },
    ],
  },
  {
    number: '3',
    tone: 'api',
    title: 'API',
    nodes: [
      {
        logos: ['fastapi', 'pydantic'],
        name: 'FastAPI + Pydantic',
        detail:
          'Passcode gate, rate limit, daily budget cap, session ownership on every resource, SSE trace stream.',
      },
    ],
  },
  {
    number: '4',
    tone: 'agent',
    title: 'Agent core',
    nodes: [
      {
        logos: ['python'],
        name: 'Bounded state machine',
        detail:
          'PLAN → ACT → OBSERVE → EVALUATE → REVISE or CLARIFY → SYNTHESIZE → VERIFY → EMIT. Limits on steps, tools, time and tokens; a partial answer instead of a hang.',
      },
      {
        name: 'Four read-only tools',
        detail:
          'list_documents, search_documents, read_document_pages, get_document_outline. Results are untrusted data.',
      },
      {
        name: 'Citation verifier',
        detail:
          'Provenance, page, then the quote must be literal text on the cited page. Unsupported claims are dropped.',
      },
    ],
  },
  {
    number: '5',
    tone: 'data',
    title: 'Data and model services',
    nodes: [
      {
        logos: ['postgresql'],
        name: 'PostgreSQL + pgvector',
        detail:
          'Source of truth: pages, chunks (HNSW vectors, full-text index), turns, trace events, evidence, citations.',
      },
      {
        logos: ['redis'],
        name: 'Redis',
        detail:
          'Session state, search cache keyed by corpus version, ingest progress, rate limits, daily budget. Optional: Postgres fallback.',
      },
      {
        logos: ['onnx'],
        name: 'Local embeddings',
        detail:
          'bge-small-en-v1.5 on ONNX Runtime. No per-query embedding cost.',
      },
      {
        logos: ['openrouter'],
        name: 'OpenRouter → LLM',
        detail:
          'One OpenAI-compatible client; model and key are configuration. Temperature 0, fixed seed.',
      },
    ],
  },
]

const ingestion = [
  'PDF upload',
  'Parse and clean',
  'Chunk 200 / 30',
  'Embed',
  'Index',
]

const patterns = [
  ['Idempotent ingest', 'The same file (SHA-256) is never indexed twice.'],
  ['Source of truth', 'Postgres is durable; Redis only accelerates.'],
  ['Degrades, not dies', 'Redis down: status "degraded", requests still work.'],
  ['Audit log', 'Every action is a stored, replayable trace event.'],
  ['Versioned', 'corpus_version keys the cache; prompt_version is recorded.'],
  ['Bounded loop', 'Explicit limits; duplicate calls blocked; retries once.'],
]

const productionLane = [
  ['Queue workers', 'Ingest off the request path, with retries'],
  ['Object storage', 'PDFs in S3-compatible storage, not a volume'],
  ['Dedicated vector tier', 'Past a few hundred thousand chunks'],
  ['Reranker', 'Only if it wins on evaluation data'],
  ['SSO and tenants', 'Replace the demo passcode'],
  ['Tracing and alerts', 'OpenTelemetry, cost and error dashboards'],
]

function RulesAsData() {
  const config = useQuery({
    queryKey: ['config'],
    queryFn: api.getConfig,
    retry: false,
  })
  const c = config.data
  return (
    <section className="hld-rules" aria-labelledby="hld-rules-title">
      <h3 id="hld-rules-title">Rules are data, not code</h3>
      <p>
        Everything below is read live from this deployment (
        <code>GET /api/v1/config</code>) and changed with environment variables.
        The prompt is versioned and recorded on every turn.
      </p>
      {c ? (
        <dl>
          <div>
            <dt>Model</dt>
            <dd>{c.model.name}</dd>
          </div>
          <div>
            <dt>Prompt version</dt>
            <dd>{c.model.prompt_version}</dd>
          </div>
          <div>
            <dt>Chunks</dt>
            <dd>
              {c.retrieval.chunk_tokens} tokens,{' '}
              {c.retrieval.chunk_overlap_tokens} overlap
            </dd>
          </div>
          <div>
            <dt>Retrieval</dt>
            <dd>vector + full text, {c.retrieval.fusion}</dd>
          </div>
          <div>
            <dt>Steps / tools</dt>
            <dd>
              {c.agent_limits.max_steps} / {c.agent_limits.max_tool_calls}
            </dd>
          </div>
          <div>
            <dt>Time / tokens</dt>
            <dd>
              {c.agent_limits.turn_timeout_seconds}s /{' '}
              {c.agent_limits.max_tokens_per_turn}
            </dd>
          </div>
          <div>
            <dt>Rate limit</dt>
            <dd>{c.protections.rate_limit_per_minute} per minute</dd>
          </div>
          <div>
            <dt>Daily budget</dt>
            <dd>${c.protections.daily_budget_usd.toFixed(2)}</dd>
          </div>
        </dl>
      ) : (
        <p className="hld-muted">
          {config.isError
            ? 'The configuration endpoint is not reachable.'
            : 'Loading configuration…'}
        </p>
      )}
    </section>
  )
}

export function SystemDiagram() {
  return (
    <div className="hld">
      <div className="hld-main">
        <ol className="hld-layers" aria-label="System layers">
          {layers.map((layer) => (
            <li key={layer.number} className={`hld-layer tone-${layer.tone}`}>
              <div className="hld-layer-head">
                <span className="hld-number" aria-hidden="true">
                  {layer.number}
                </span>
                <h3>{layer.title}</h3>
              </div>
              <div className="hld-nodes">
                {layer.nodes.map((node) => (
                  <div key={node.name} className="hld-node">
                    <div className="hld-node-title">
                      {node.logos?.map((logo) => (
                        <img
                          key={logo}
                          src={`/logos/${logo}.svg`}
                          alt=""
                          width="22"
                          height="22"
                        />
                      ))}
                      <strong>{node.name}</strong>
                    </div>
                    <p>{node.detail}</p>
                  </div>
                ))}
              </div>
            </li>
          ))}
        </ol>

        <aside className="hld-ingest" aria-label="Ingestion pipeline">
          <div className="hld-layer-head">
            <span className="hld-number" aria-hidden="true">
              6
            </span>
            <h3>Ingestion pipeline</h3>
          </div>
          <ol>
            {ingestion.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          <p>
            One transaction per document, progress in Redis, then{' '}
            <code>corpus_version</code> is bumped so stale search results can
            never be served.
          </p>
        </aside>
      </div>

      <section className="hld-lane" aria-labelledby="hld-lane-title">
        <h3 id="hld-lane-title">
          Production scale: designed for, not built today
        </h3>
        <ul>
          {productionLane.map(([name, detail]) => (
            <li key={name}>
              <strong>{name}</strong>
              <span>{detail}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="hld-patterns" aria-labelledby="hld-patterns-title">
        <h3 id="hld-patterns-title">Patterns in use</h3>
        <ul>
          {patterns.map(([name, detail]) => (
            <li key={name}>
              <strong>{name}</strong>
              <span>{detail}</span>
            </li>
          ))}
        </ul>
      </section>

      <RulesAsData />
      <p className="hld-credit">
        Logos are trademarks of their owners, shown only to identify the
        technologies used.
      </p>
    </div>
  )
}
