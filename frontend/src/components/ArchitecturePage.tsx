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

export function ArchitecturePage({ onBack }: { onBack: () => void }) {
  return (
    <main className="page">
      <div className="page-inner">
        <button className="page-back" type="button" onClick={onBack}>
          <span aria-hidden="true">←</span> Back to workspace
        </button>
        <header className="page-head">
          <p className="eyebrow">System design</p>
          <h1>How PolicyPilot is built</h1>
          <p>
            A question goes down through five layers and comes back as an answer
            whose citations were checked against the page text.
          </p>
        </header>
        <SystemDiagram />
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
