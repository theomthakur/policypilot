import { PolicyPilotMark } from './PolicyPilotMark'

interface ProjectGuideProps {
  view: 'architecture' | 'presentation'
  onBack: () => void
}

const architectureLayers = [
  {
    label: 'Experience',
    items: ['React workspace', 'Citation viewer', 'Execution trace'],
  },
  {
    label: 'Application',
    items: ['FastAPI boundary', 'Session isolation', 'Bounded agent loop'],
  },
  {
    label: 'Intelligence',
    items: ['Read-only tools', 'Hybrid retrieval', 'Citation verifier'],
  },
  {
    label: 'State',
    items: ['PostgreSQL + pgvector', 'Redis cache', 'PDF volume'],
  },
]

const presentationSteps = [
  [
    '00:00',
    'Problem and invariant',
    'Why a policy answer must be inspectable.',
  ],
  [
    '01:30',
    'Live grounded answer',
    'Cross-document answer, trace and exact page evidence.',
  ],
  ['06:00', 'Why an agent', 'Weak evidence changes the next action.'],
  [
    '08:00',
    'High-level design',
    'Boundaries, state, tools and failure behavior.',
  ],
  [
    '13:30',
    'Measured evaluation',
    'Agent versus baseline, including cost and failures.',
  ],
  ['16:00', 'Operations', 'Compose, persistence and Redis degradation.'],
  [
    '17:30',
    'Trade-offs',
    'What works now, what remains, and scaling thresholds.',
  ],
]

function ArchitectureView() {
  return (
    <>
      <div className="guide-hero-copy">
        <p className="eyebrow">High-level design</p>
        <h1>A bounded agent around evidence, not an answer generator.</h1>
        <p>
          PostgreSQL is authoritative, Redis is disposable acceleration, and
          every response passes through an authorization and citation boundary.
        </p>
      </div>

      <div className="architecture-flow" aria-label="PolicyPilot architecture">
        <div className="flow-node flow-user">Browser</div>
        <span className="flow-arrow" aria-hidden="true">
          →
        </span>
        <div className="flow-node flow-gateway">Caddy</div>
        <span className="flow-arrow" aria-hidden="true">
          →
        </span>
        <div className="flow-node flow-api">FastAPI</div>
        <span className="flow-arrow" aria-hidden="true">
          →
        </span>
        <div className="flow-node flow-agent">Agent loop</div>
        <span className="flow-arrow" aria-hidden="true">
          →
        </span>
        <div className="flow-node flow-evidence">Verified answer</div>
      </div>

      <div className="architecture-layers">
        {architectureLayers.map((layer, index) => (
          <article key={layer.label}>
            <span className="layer-number">0{index + 1}</span>
            <h2>{layer.label}</h2>
            <ul>
              {layer.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>

      <div className="guide-split">
        <article className="guide-card">
          <p className="eyebrow">Ingestion path</p>
          <h2>PDF to authorized evidence</h2>
          <ol className="numbered-flow">
            <li>Validate, hash and scope the upload to a session.</li>
            <li>Parse by physical page and create page-bounded chunks.</li>
            <li>Embed locally and build vector plus full-text indexes.</li>
            <li>Publish atomically, then advance the corpus version.</li>
          </ol>
        </article>
        <article className="guide-card">
          <p className="eyebrow">Query path</p>
          <h2>Question to verified answer</h2>
          <ol className="numbered-flow">
            <li>Load authorized state and plan bounded tool actions.</li>
            <li>Search, inspect results, revise, read or clarify.</li>
            <li>Synthesize only from evidence seen during the turn.</li>
            <li>Verify citations and remove unsupported claims.</li>
          </ol>
        </article>
      </div>

      <div className="invariant-strip">
        <strong>Core invariant</strong>
        <span>
          A material claim cannot be shown as verified unless its evidence was
          returned in this turn and resolves to the cited document page.
        </span>
      </div>
    </>
  )
}

function PresentationView() {
  return (
    <>
      <div className="guide-hero-copy">
        <p className="eyebrow">20-minute walkthrough</p>
        <h1>Prove the product first. Explain the engineering second.</h1>
        <p>
          The presentation is organized around one live workflow, one HLD and
          measured evidence rather than a feature-heavy slide deck.
        </p>
      </div>

      <div className="presentation-timeline">
        {presentationSteps.map(([time, title, description], index) => (
          <article key={time}>
            <div className="timeline-marker">
              <span>{index + 1}</span>
            </div>
            <time>{time}</time>
            <div>
              <h2>{title}</h2>
              <p>{description}</p>
            </div>
          </article>
        ))}
      </div>

      <div className="guide-split presentation-cards">
        <article className="guide-card">
          <p className="eyebrow">Live demo</p>
          <h2>Four moments to show</h2>
          <ul className="check-list">
            <li>Multi-document answer with exact page citations.</li>
            <li>Weak evidence followed by a revised action.</li>
            <li>Clarification with the original intent retained.</li>
            <li>Controlled timeout with bounded recovery.</li>
          </ul>
        </article>
        <article className="guide-card">
          <p className="eyebrow">Evaluation</p>
          <h2>Numbers, not adjectives</h2>
          <ul className="metric-list">
            <li>
              <strong>Completion</strong>
              <span>agent vs baseline</span>
            </li>
            <li>
              <strong>Citations</strong>
              <span>precision and coverage</span>
            </li>
            <li>
              <strong>Latency</strong>
              <span>p50, p95 and stage time</span>
            </li>
            <li>
              <strong>Cost</strong>
              <span>tokens and USD per case</span>
            </li>
          </ul>
        </article>
      </div>

      <div className="presentation-rule">
        <PolicyPilotMark />
        <div>
          <strong>Keep the claim honest.</strong>
          <span>
            Fake-model CI, injected faults and real-model evaluation are shown
            separately. Planned capabilities stay labelled planned.
          </span>
        </div>
      </div>
    </>
  )
}

export function ProjectGuide({ view, onBack }: ProjectGuideProps) {
  return (
    <main className="project-guide">
      <div className="guide-container">
        <button className="guide-back" type="button" onClick={onBack}>
          <span aria-hidden="true">←</span> Back to workspace
        </button>
        {view === 'architecture' ? <ArchitectureView /> : <PresentationView />}
      </div>
    </main>
  )
}
