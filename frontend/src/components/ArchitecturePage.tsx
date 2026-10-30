import { FlowDiagram } from './FlowDiagram'
import './Pages.css'

export function ArchitecturePage({ onBack }: { onBack: () => void }) {
  return (
    <main className="page">
      <div className="page-inner">
        <button className="page-back" type="button" onClick={onBack}>
          <span aria-hidden="true">←</span> Back to workspace
        </button>
        <header className="page-head">
          <p className="eyebrow">System design</p>
          <h1>From a PDF to an answer you can check.</h1>
          <p>
            Two flows share one database. A document is split, embedded and
            indexed; a question is answered by an agent whose every quote is
            checked against the page.
          </p>
        </header>
        <FlowDiagram />
        <p className="fd-legend">
          Solid boxes run today. The dashed box is written and rendered but has
          not been run on a real OpenShift cluster.
        </p>
      </div>
    </main>
  )
}
