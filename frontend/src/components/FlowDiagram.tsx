import './FlowDiagram.css'

interface Node {
  title: string
  detail: string
  logo?: string
  badge?: string
  note?: string
}

interface Lane {
  number: string
  tone: 'ingest' | 'query' | 'shared' | 'run'
  title: string
  blurb: string
  nodes: Node[]
  linked?: boolean
}

const lanes: Lane[] = [
  {
    number: '1',
    tone: 'ingest',
    title: 'A document comes in',
    blurb: 'Upload to searchable evidence',
    linked: true,
    nodes: [
      {
        title: 'Upload',
        logo: 'react',
        detail:
          'PDF from the browser. Type and size checked, SHA-256 to skip duplicates.',
      },
      {
        title: 'File storage',
        badge: 'S3',
        detail: 'A local volume, or S3-compatible storage in the cluster.',
      },
      {
        title: 'Job queue',
        logo: 'postgresql',
        detail:
          'A Postgres table with a lease and retries. A worker picks the job up.',
      },
      {
        title: 'Parse',
        logo: 'python',
        detail:
          'Page by page with PyMuPDF. Repeated headers and footers removed.',
      },
      {
        title: 'Chunk',
        badge: '200 tok',
        detail:
          'About 200 tokens each, never across a page. The page number is kept.',
      },
      {
        title: 'Embed',
        logo: 'onnx',
        detail: 'bge-small runs locally on ONNX. No per-question cost.',
      },
      {
        title: 'Index',
        logo: 'postgresql',
        detail: 'pgvector (HNSW) and full-text (GIN). Published all at once.',
      },
    ],
  },
  {
    number: '2',
    tone: 'query',
    title: 'A question comes in',
    blurb: 'From question to a checked answer',
    linked: true,
    nodes: [
      {
        title: 'Browser',
        logo: 'react',
        detail: 'React and TypeScript: chat, citations, live trace.',
      },
      {
        title: 'Gateway',
        logo: 'nginx',
        detail:
          'nginx serves the app and proxies /api. Caddy adds HTTPS in production.',
      },
      {
        title: 'API',
        logo: 'fastapi',
        detail:
          'FastAPI: sign-in (OIDC), rate limit, daily budget, session ownership.',
      },
      {
        title: 'Agent loop',
        logo: 'python',
        detail:
          'Plan, search, judge, read pages, search again. At most 8 steps and 6 tool calls.',
      },
      {
        title: 'Tools and search',
        logo: 'postgresql',
        detail:
          'List, search, read pages, outline. Hybrid search: meaning and keywords merged.',
      },
      {
        title: 'Model',
        logo: 'openrouter',
        detail:
          'OpenRouter: GPT-4o mini runs the agent, while a stronger model judges ambiguity.',
      },
      {
        title: 'Verifier',
        badge: 'quote check',
        detail:
          'Each quote must appear on the cited page, or the claim is repaired or dropped.',
      },
      {
        title: 'Answer',
        badge: 'cited',
        detail:
          'A cited answer, a clarifying question, or "not found". The trace streams live.',
      },
    ],
  },
  {
    number: '3',
    tone: 'shared',
    title: 'Shared services',
    blurb: 'What both flows rely on',
    nodes: [
      {
        title: 'PostgreSQL 16',
        logo: 'postgresql',
        detail:
          'Documents, chunks, vectors, sessions, turns, traces and the job queue.',
      },
      {
        title: 'Redis',
        logo: 'redis',
        detail:
          'Search cache, hot session state, rate and budget counters. Optional: the app runs without it.',
      },
      {
        title: 'Object storage',
        badge: 'S3',
        detail:
          'The original PDFs. Local volume in Compose, SeaweedFS in Kubernetes.',
      },
      {
        title: 'Trace and cost',
        badge: 'events',
        detail:
          'Every step, token count and estimated cost is stored with the turn.',
      },
    ],
  },
  {
    number: '4',
    tone: 'run',
    title: 'Where it runs',
    blurb: 'Same images, three targets',
    nodes: [
      {
        title: 'Docker Compose',
        logo: 'docker',
        detail:
          'The full stack on one machine with health checks and volumes. Verified.',
      },
      {
        title: 'Kubernetes',
        badge: 'K8s',
        detail:
          'Kustomize base. Tested on kind with Calico network policies, 2 API and 2 worker pods. Verified.',
      },
      {
        title: 'OpenShift',
        badge: 'OpenShift',
        note: 'Overlay written and rendered. Not run on a real cluster.',
        detail: 'Same manifests with OpenShift-safe security settings.',
      },
      {
        title: 'CI',
        logo: 'githubactions',
        detail:
          'GitHub Actions on every push: lint, types, tests, image builds.',
      },
    ],
  },
]

function NodeCard({ node }: { node: Node }) {
  return (
    <div className={`fd-node${node.note ? ' is-planned' : ''}`}>
      <div className="fd-node-head">
        {node.logo && (
          <img src={`/logos/${node.logo}.svg`} alt="" width="18" height="18" />
        )}
        {node.badge && <span className="fd-badge">{node.badge}</span>}
        <strong>{node.title}</strong>
      </div>
      <p>{node.detail}</p>
      {node.note && <em>{node.note}</em>}
    </div>
  )
}

export function FlowDiagram() {
  return (
    <div
      className="fd"
      role="img"
      aria-label="System flow from upload to answer"
    >
      {lanes.map((lane) => (
        <section className={`fd-lane fd-${lane.tone}`} key={lane.number}>
          <header>
            <span className="fd-number">{lane.number}</span>
            <div>
              <h2>{lane.title}</h2>
              <p>{lane.blurb}</p>
            </div>
          </header>
          <div className="fd-row">
            {lane.nodes.map((node, index) => (
              <div className="fd-cell" key={node.title}>
                <NodeCard node={node} />
                {lane.linked &&
                  index % 4 !== 3 &&
                  index < lane.nodes.length - 1 && (
                    <span className="fd-arrow" aria-hidden="true">
                      →
                    </span>
                  )}
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
