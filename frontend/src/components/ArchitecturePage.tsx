import { SystemDiagram } from './SystemDiagram'
import './Pages.css'

const decisions = [
  [
    'Hand-written agent loop',
    'Every state and limit is visible code, not a framework default.',
  ],
  [
    'One database for everything',
    'Postgres with pgvector holds vectors, text search and the audit trail.',
  ],
  [
    'Measured retrieval',
    '200-token chunks and hybrid search won on our gold pages; a reranker lost.',
  ],
  [
    'Verify before showing',
    'A citation is shown only if its quote is literal text on that page.',
  ],
]

const criticalFlows = [
  {
    label: 'Ingest',
    title: 'PDF → searchable evidence',
    steps: [
      'Validate size and type, then hash for idempotency.',
      'Parse physical pages and clean repeated noise.',
      'Create page-bounded chunks, embeddings and hybrid indexes.',
      'Publish the completed document atomically into the session corpus.',
    ],
  },
  {
    label: 'Answer',
    title: 'Question → verified response',
    steps: [
      'Authorize the session and load the bounded corpus state.',
      'Search, inspect evidence, then revise, read pages or clarify.',
      'Draft only from evidence returned in this specific turn.',
      'Verify provenance, page location and literal quote before display.',
    ],
  },
]

export function ArchitecturePage({ onBack }: { onBack: () => void }) {
  return (
    <main className="page">
      <div className="page-inner">
        <button className="page-back" type="button" onClick={onBack}>
          <span aria-hidden="true">←</span> Back to workspace
        </button>
        <header className="page-head">
          <p className="eyebrow">System design · high-level architecture</p>
          <h1>How PolicyPilot earns the right to answer.</h1>
          <p>
            A question moves through five explicit layers and returns only after
            the cited evidence is checked against the original page text.
          </p>
        </header>
        <section className="hld-intro" aria-label="Architecture goals">
          <article>
            <span>01</span>
            <strong>Private by boundary</strong>
            <p>
              Document access is enforced server-side before source text reaches
              the model.
            </p>
          </article>
          <article>
            <span>02</span>
            <strong>Agentic by behavior</strong>
            <p>
              The next step responds to tool results; it is not a fixed
              retrieve-then-generate chain.
            </p>
          </article>
          <article>
            <span>03</span>
            <strong>Trustworthy by proof</strong>
            <p>
              Every visible citation must be traceable to literal text on the
              cited page.
            </p>
          </article>
        </section>
        <SystemDiagram />
        <section
          className="hld-flow-section"
          aria-labelledby="critical-flows-title"
        >
          <div>
            <p className="eyebrow">Critical paths</p>
            <h2 id="critical-flows-title">
              The two flows that matter in a live demo.
            </h2>
          </div>
          <div className="hld-flow-grid">
            {criticalFlows.map((flow) => (
              <article key={flow.label}>
                <p>
                  <span>{flow.label}</span> {flow.title}
                </p>
                <ol>
                  {flow.steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
              </article>
            ))}
          </div>
        </section>
        <section className="page-decisions" aria-labelledby="decisions-title">
          <h2 id="decisions-title">Four decisions worth knowing</h2>
          <ul>
            {decisions.map(([title, detail]) => (
              <li key={title}>
                <strong>{title}</strong>
                <span>{detail}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </main>
  )
}
