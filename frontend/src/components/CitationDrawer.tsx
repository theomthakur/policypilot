import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, errorMessage } from '../api/client'
import type { Citation } from '../api/types'

interface CitationDrawerProps {
  citation: Citation | null
  onClose: () => void
  onViewPdf?: (citation: Citation) => void
}

function HighlightedText({ text, quote }: { text: string; quote: string }) {
  if (!quote.trim()) return <>{text}</>
  const index = text.toLocaleLowerCase().indexOf(quote.toLocaleLowerCase())
  if (index < 0) return <>{text}</>
  return (
    <>
      {text.slice(0, index)}
      <mark>{text.slice(index, index + quote.length)}</mark>
      {text.slice(index + quote.length)}
    </>
  )
}

export function CitationDrawer({
  citation,
  onClose,
  onViewPdf,
}: CitationDrawerProps) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const page = useQuery({
    queryKey: ['page', citation?.document_id, citation?.page],
    queryFn: () => api.getPage(citation!.document_id, citation!.page),
    enabled: citation !== null,
  })

  useEffect(() => {
    if (!citation) return
    closeRef.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [citation, onClose])

  if (!citation) return null

  return (
    <div
      className="drawer-layer"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <aside
        className="citation-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="citation-title"
      >
        <header>
          <div>
            <p className="eyebrow">
              Verified source · Citation {citation.number}
            </p>
            <h2 id="citation-title">{citation.document_title}</h2>
            <p>
              PDF page {citation.page}
              {onViewPdf && (
                <>
                  {' · '}
                  <button
                    className="link-button"
                    type="button"
                    onClick={() => onViewPdf(citation)}
                  >
                    Open the PDF at this page
                  </button>
                </>
              )}
            </p>
          </div>
          <button
            ref={closeRef}
            className="icon-button"
            type="button"
            onClick={onClose}
            aria-label="Close citation"
          >
            ×
          </button>
        </header>
        <div
          className={`verification-strip verification-${citation.validation_status}`}
        >
          <span aria-hidden="true">✓</span>
          {citation.validation_status === 'verified'
            ? 'Quote verified on this page'
            : `Citation ${citation.validation_status}`}
        </div>
        <div className="page-view">
          {page.isLoading && (
            <p className="inline-status">
              <span className="spinner" /> Loading page…
            </p>
          )}
          {page.isError && (
            <p className="inline-error" role="alert">
              {errorMessage(page.error)}
            </p>
          )}
          {page.data && (
            <div className="page-paper">
              <div className="page-number">{page.data.page}</div>
              <p>
                <HighlightedText text={page.data.text} quote={citation.quote} />
              </p>
            </div>
          )}
        </div>
        <footer>
          <div>
            <span className="quote-label">Supporting quote</span>
            <blockquote>“{citation.quote}”</blockquote>
          </div>
        </footer>
      </aside>
    </div>
  )
}
