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
        detail: 'Chat, citation drawer, live trace, uploads.',
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
        detail: 'Serves the app and proxies /api.',
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
          'Sign-in, rate limit, budget cap, ownership checks, SSE stream.',
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
          'Plan, search, judge, search again or ask, answer, verify. Hard limits.',
      },
      {
        name: 'Four read-only tools',
        detail:
          'List, search, read pages, outline. Results are untrusted data.',
      },
      {
        name: 'Citation verifier',
        detail: 'The quote must be literal text on the cited page.',
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
        detail: 'Source of truth: vectors, text search, turns, trace.',
      },
      {
        logos: ['redis'],
        name: 'Redis',
        detail: 'Sessions, search cache, rate limits, budget. Optional.',
      },
      {
        logos: ['onnx'],
        name: 'Local embeddings',
        detail: 'bge-small on ONNX. No per-query cost.',
      },
      {
        logos: ['openrouter'],
        name: 'OpenRouter → LLM',
        detail: 'One client; model and key are configuration.',
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
  [
    'Durable jobs',
    'Questions and uploads are stored jobs a new worker can resume.',
  ],
]

const productionLane = [
  ['Object storage', 'PDFs in S3-compatible storage, so workers can scale out'],
  ['Managed database', 'Replication and point-in-time backups'],
  ['Dedicated vector tier', 'Past a few hundred thousand chunks'],
  ['Reranker', 'Only if it wins on evaluation data'],
  [
    'University SSO and roles',
    'Sign-in works with any OpenID provider; roles are not built',
  ],
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
      <h2 id="hld-rules-title">Rules are data, not code</h2>
      <p>
        Read live from this deployment and changed with environment variables.
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
                <h2>{layer.title}</h2>
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
            <h2>Ingestion pipeline</h2>
          </div>
          <ol>
            {ingestion.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          <p>
            One transaction per document. Stale search results are never served.
          </p>
        </aside>
      </div>

      <section className="hld-chips-block" aria-labelledby="hld-lane-title">
        <h2 id="hld-lane-title">
          Production scale: designed for, not built today
        </h2>
        <ul className="hld-chips hld-chips-dashed">
          {productionLane.map(([name, detail]) => (
            <li key={name} title={detail}>
              {name}
            </li>
          ))}
        </ul>
      </section>

      <section className="hld-chips-block" aria-labelledby="hld-patterns-title">
        <h2 id="hld-patterns-title">Patterns in use</h2>
        <ul className="hld-chips">
          {patterns.map(([name, detail]) => (
            <li key={name} title={detail}>
              {name}
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
