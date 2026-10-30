import { useEffect } from 'react'
import { CloseIcon } from './CloseIcon'
import { documentFileUrl } from '../api/client'

export interface ViewerTarget {
  id: string
  title: string
  page?: number
}

/** The original PDF in the browser's own viewer, opened at a page. */
export function PdfViewer({
  target,
  onClose,
}: {
  target: ViewerTarget | null
  onClose: () => void
}) {
  useEffect(() => {
    if (!target) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [target, onClose])

  if (!target) return null
  const url = documentFileUrl(target.id, target.page)
  return (
    <div
      className="viewer-layer"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <section
        className="pdf-viewer"
        role="dialog"
        aria-modal="true"
        aria-label={`PDF: ${target.title}`}
      >
        <header>
          <div>
            <p className="eyebrow">Original document</p>
            <h2>{target.title}</h2>
          </div>
          <div className="viewer-actions">
            <a href={url} target="_blank" rel="noreferrer">
              Open in a new tab
            </a>
            <button
              className="icon-button"
              type="button"
              onClick={onClose}
              aria-label="Close PDF"
            >
              <CloseIcon />
            </button>
          </div>
        </header>
        <iframe key={url} title={target.title} src={url} />
      </section>
    </div>
  )
}
