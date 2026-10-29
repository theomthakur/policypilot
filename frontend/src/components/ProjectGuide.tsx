import { PolicyPilotMark } from './PolicyPilotMark'
import { SystemDiagram } from './SystemDiagram'

interface ProjectGuideProps {
  view: 'architecture' | 'presentation'
  onBack: () => void
}

const layers = [
  {
    number: '01',
    title: 'Experience layer',
    detail: 'The reviewer-facing workspace',
    items: ['React + TypeScript', 'Citation drawer', 'Trace and SSE updates'],
  },
  {
    number: '02',
    title: 'Control plane',
    detail: 'The only boundary that mutates state',
    items: ['Caddy gateway', 'FastAPI API', 'Session authorization'],
  },
  {
    number: '03',
    title: 'Evidence loop',
    detail: 'A bounded decision process',
    items: ['Tool-capable LLM', 'Validated read-only tools', 'Citation verifier'],
  },
  {
    number: '04',
    title: 'Durable state',
    detail: 'Truth first, acceleration second',
    items: ['PostgreSQL + pgvector', 'Page-bounded chunks', 'Redis cache'],
  },
]

const presentationSteps = [
  ['00:00', 'The problem', 'Policy answers are useful only when the evidence is inspectable.'],
  ['00:45', 'The product', 'Run one cross-document question and open the exact source pages.'],
  ['04:30', 'The agent moment', 'Show weak evidence changing the next action—not a fixed RAG chain.'],
  ['07:00', 'The system design', 'Walk through boundaries, persistence and the citation gate.'],
  ['11:00', 'The proof', 'Compare agent and baseline with completion, citations, latency and cost.'],
  ['14:30', 'The failure path', 'Show a timeout, retry, abstention or clarification working safely.'],
  ['17:00', 'The trade-offs', 'Separate what is working now from the production-scale next step.'],
]

function Node({
  title,
  caption,
  tone = 'default',
}: {
  title: string
  caption: string
  tone?: 'default' | 'primary' | 'accent' | 'storage'
}) {
  return (
    <div className={`system-node system-node-${tone}`}>
      <strong>{title}</strong>
      <span>{caption}</span>
    </div>
  )
}

function SystemMap() {
  return (
    <section className="system-map" aria-label="PolicyPilot high-level architecture">
      <div className="system-map-heading">
        <div>
          <p className="eyebrow">System map</p>
          <h2>One trusted path from document to defensible answer.</h2>
        </div>
        <div className="system-legend" aria-label="Architecture legend">
          <span><i className="legend-user" /> interaction</span>
          <span><i className="legend-control" /> control plane</span>
          <span><i className="legend-evidence" /> evidence path</span>
        </div>
      </div>

      <div className="system-map-canvas">
        <div className="system-stage system-stage-client">
          <span className="stage-label">01 · Client</span>
          <Node title="Browser" caption="workspace + citations" />
          <Node title="React UI" caption="snapshot + SSE events" />
        </div>
        <div className="system-connector system-connector-edge"><span>HTTPS</span></div>
        <div className="system-stage system-stage-control">
          <span className="stage-label">02 · Trusted control plane</span>
          <Node title="Caddy" caption="one origin + request limits" tone="primary" />
          <Node title="FastAPI" caption="sessions, API and streams" tone="primary" />
          <Node title="Authorization" caption="session-scoped document access" tone="primary" />
        </div>
        <div className="system-connector system-connector-agent"><span>validated calls</span></div>
        <div className="system-stage system-stage-agent">
          <span className="stage-label">03 · Bounded evidence loop</span>
          <Node title="Agent orchestrator" caption="plan → act → observe" tone="accent" />
          <Node title="Read-only tools" caption="list, search, read pages" tone="accent" />
          <Node title="Citation verifier" caption="provenance, page, quote" tone="accent" />
        </div>
        <div className="system-connector system-connector-data"><span>authorized evidence</span></div>
        <div className="system-stage system-stage-data">
          <span className="stage-label">04 · Data and model services</span>
          <Node title="PostgreSQL + pgvector" caption="durable state + hybrid retrieval" tone="storage" />
          <Node title="Redis" caption="reconstructable cache only" tone="storage" />
          <Node title="Tool-capable LLM" caption="chooses next bounded action" tone="storage" />
        </div>
      </div>

      <div className="system-map-notes">
        <p><strong>Ingest</strong> Validate PDF → hash → parse by physical page → chunk → embed → publish atomically.</p>
        <p><strong>Answer</strong> Authorize → retrieve → inspect → revise / read / clarify → verify → stream the result.</p>
      </div>
    </section>
  )
}

function ArchitectureView() {
  return (
    <>
      <div className="guide-kicker-row">
        <p className="eyebrow">System design · High-level architecture</p>
        <span className="guide-version">HLD / reviewer view</span>
      </div>
      <div className="guide-hero-copy guide-hero-architecture">
        <h1>Every answer has a traceable path back to the source.</h1>
        <p>
          PolicyPilot is a bounded research system for a small, private PDF corpus.
          The model can choose its next read-only action, but server-side boundaries decide
          what it can access, when it stops, and whether its citations are allowed through.
        </p>
      </div>

      <SystemMap />

      <section
        className="guide-hld"
        aria-label="Full system design with technology stack"
      >
        <p className="eyebrow">Full system design · technology stack</p>
        <h2>The whole system, layer by layer.</h2>
        <SystemDiagram />
      </section>

      <section className="design-principles" aria-label="Design principles">
        <article><span>01</span><strong>Evidence before prose</strong><p>Claims are verified against retrieved page-level evidence.</p></article>
        <article><span>02</span><strong>Bounded autonomy</strong><p>Tools, retries, model turns and wall time have explicit limits.</p></article>
        <article><span>03</span><strong>Durable truth</strong><p>PostgreSQL is authoritative; cache loss must not change correctness.</p></article>
      </section>

      <section className="layer-section">
        <div className="section-heading">
          <p className="eyebrow">Component responsibilities</p>
          <h2>Each boundary has one job.</h2>
        </div>
        <div className="architecture-layers">
          {layers.map((layer) => (
            <article key={layer.title}>
              <span className="layer-number">{layer.number}</span>
              <p>{layer.detail}</p>
              <h3>{layer.title}</h3>
              <ul>{layer.items.map((item) => <li key={item}>{item}</li>)}</ul>
            </article>
          ))}
        </div>
      </section>

      <section className="flow-section">
        <div className="section-heading">
          <p className="eyebrow">Critical paths</p>
          <h2>What happens when a document arrives or a question is asked.</h2>
        </div>
        <div className="guide-split guide-flow-cards">
          <article className="guide-card flow-card">
            <div className="card-label"><span>Path A</span> Ingestion</div>
            <h3>Make a document searchable without losing its location.</h3>
            <ol className="numbered-flow">
              <li>Validate file type and size; hash for session-scoped idempotency.</li>
              <li>Parse by physical page; remove repeated header and footer noise.</li>
              <li>Create overlapping, page-bounded chunks and local embeddings.</li>
              <li>Write document, pages and indexes, then mark the corpus version ready.</li>
            </ol>
          </article>
          <article className="guide-card flow-card">
            <div className="card-label"><span>Path B</span> Answer</div>
            <h3>Use evidence to decide whether an answer is justified.</h3>
            <ol className="numbered-flow">
              <li>Load session-authorized corpus state and apply budgets.</li>
              <li>Use a tool, inspect its result, then search again, read pages or clarify.</li>
              <li>Draft only from evidence seen during the current turn.</li>
              <li>Verify citation provenance, page location and support before streaming.</li>
            </ol>
          </article>
        </div>
      </section>

      <section className="guide-split decision-cards">
        <article className="guide-card">
          <p className="eyebrow">Safety and failure behavior</p>
          <h3>Failure is a product state, not a hidden exception.</h3>
          <ul className="check-list">
            <li>Retrieved text is treated as untrusted data, never tool instructions.</li>
            <li>Tools cannot run arbitrary URLs, shell commands, SQL or file paths.</li>
            <li>Timeouts have one bounded retry; duplicate calls are detected.</li>
            <li>Weak evidence produces clarification, partial answer or abstention.</li>
          </ul>
        </article>
        <article className="guide-card">
          <p className="eyebrow">Scale deliberately</p>
          <h3>Move beyond this shape only when the workload asks for it.</h3>
          <ul className="check-list">
            <li>More queries: stateless API replicas and provider concurrency control.</li>
            <li>More ingestion: durable queue, leased workers and object storage.</li>
            <li>More tenants: tenant identity, ACL-aware retrieval and audit logs.</li>
            <li>More availability: managed data stores and independent workers.</li>
          </ul>
        </article>
      </section>

      <div className="invariant-strip">
        <strong>System invariant</strong>
        <span>A material claim is never called verified unless its evidence was returned this turn and resolves to the cited document page.</span>
      </div>
    </>
  )
}

function PresentationView() {
  return (
    <>
      <div className="guide-kicker-row">
        <p className="eyebrow">Presentation · Demo narrative</p>
        <span className="guide-version">18–20 minute walkthrough</span>
      </div>
      <div className="guide-hero-copy guide-hero-presentation">
        <h1>Start with proof. Use the architecture to explain why it works.</h1>
        <p>
          This is a reviewer walkthrough, not a slide-heavy product pitch: one useful
          question, one observable agent decision, one HLD, and honest evaluation evidence.
        </p>
      </div>

      <section className="presentation-opening">
        <PolicyPilotMark />
        <div>
          <span>The opening, in one breath</span>
          <p>“PolicyPilot searches, inspects and combines evidence across a bounded policy corpus. It can retrieve again, ask a clarification, or stop when the evidence is insufficient—and every material claim links to a page the reviewer can open.”</p>
        </div>
      </section>

      <section className="presentation-timeline" aria-label="Presentation timeline">
        <div className="timeline-heading"><p className="eyebrow">Run of show</p><span>What to show · Why it matters</span></div>
        {presentationSteps.map(([time, title, description], index) => (
          <article key={time}>
            <div className="timeline-marker"><span>{String(index + 1).padStart(2, '0')}</span></div>
            <time>{time}</time>
            <div><h2>{title}</h2><p>{description}</p></div>
          </article>
        ))}
      </section>

      <section className="guide-split presentation-cards">
        <article className="guide-card">
          <p className="eyebrow">Live demo script</p>
          <h3>Four visual moments worth showing.</h3>
          <ol className="numbered-flow">
            <li>Ask one multi-document question and open the exact cited pages.</li>
            <li>Show weak initial evidence causing a query revision or page read.</li>
            <li>Ask an ambiguous question; carry the original intent through clarification.</li>
            <li>Show the controlled timeout path and a bounded recovery or partial result.</li>
          </ol>
        </article>
        <article className="guide-card">
          <p className="eyebrow">Evaluation story</p>
          <h3>Compare the agent to the simplest credible baseline.</h3>
          <ul className="metric-list">
            <li><strong>Completion</strong><span>same corpus, same task set</span></li>
            <li><strong>Citations</strong><span>precision and claim coverage</span></li>
            <li><strong>Latency</strong><span>p50, p95 and stage timings</span></li>
            <li><strong>Cost</strong><span>tokens and USD per case</span></li>
          </ul>
        </article>
      </section>

      <section className="presentation-evidence-grid">
        <article><span>Show</span><strong>A real trace</strong><p>Action summaries and tool results—not hidden reasoning.</p></article>
        <article><span>Measure</span><strong>A real trade-off</strong><p>One case where the baseline is faster and enough, and one where the agent earns its extra work.</p></article>
        <article><span>Disclose</span><strong>What is planned</strong><p>Keep fake-model tests, injected faults and real-model results explicitly separate.</p></article>
      </section>

      <div className="presentation-rule">
        <PolicyPilotMark />
        <div><strong>Hackathon rule: one number per claim.</strong><span>Use saved traces, raw evaluation results and a signed-out deployment smoke test. Do not let a diagram or a polished screen stand in for evidence.</span></div>
      </div>
    </>
  )
}

export function ProjectGuide({ view, onBack }: ProjectGuideProps) {
  return (
    <main className="project-guide">
      <div className="guide-container">
        <button className="guide-back" type="button" onClick={onBack}><span aria-hidden="true">←</span> Back to workspace</button>
        {view === 'architecture' ? <ArchitectureView /> : <PresentationView />}
      </div>
    </main>
  )
}
