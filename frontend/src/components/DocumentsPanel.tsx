import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errorMessage, uploadDocument } from '../api/client'
import type { IngestionRun, PolicyDocument } from '../api/types'

function StatusDot({ status }: { status: PolicyDocument['status'] }) {
  return <span className={`status-dot status-${status}`} aria-hidden="true" />
}

export function DocumentsPanel({
  onView,
}: {
  onView?: (document: PolicyDocument) => void
}) {
  const queryClient = useQueryClient()
  // Folders start open; a folder the person closes stays closed while they move between tabs.
  const [closedFolders, setClosedFolders] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('pp_closed_folders') ?? '[]')
    } catch {
      return []
    }
  })
  const setFolderOpen = (key: string, open: boolean) => {
    setClosedFolders((current) => {
      const next = open
        ? current.filter((item) => item !== key)
        : [...new Set([...current, key])]
      try {
        localStorage.setItem('pp_closed_folders', JSON.stringify(next))
      } catch {
        // A convenience only.
      }
      return next
    })
  }
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadNotice, setUploadNotice] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [run, setRun] = useState<IngestionRun | null>(null)

  const documents = useQuery({
    queryKey: ['documents'],
    queryFn: api.listDocuments,
    refetchInterval: (query) =>
      query.state.data?.some(
        (document) =>
          document.status !== 'ready' && document.status !== 'failed',
      )
        ? 1500
        : false,
  })

  useEffect(() => {
    if (!run || run.status === 'ready' || run.status === 'failed') return
    const timer = window.setInterval(async () => {
      try {
        const next = await api.getIngestion(run.id)
        setRun(next)
        if (next.status === 'ready' || next.status === 'failed') {
          window.clearInterval(timer)
          void queryClient.invalidateQueries({ queryKey: ['documents'] })
        }
      } catch (error) {
        setUploadError(errorMessage(error))
        window.clearInterval(timer)
      }
    }, 1000)
    return () => window.clearInterval(timer)
  }, [queryClient, run])

  const handleFile = async (file?: File) => {
    if (!file) return
    setUploadError(null)
    setUploadNotice(null)
    if (
      file.type !== 'application/pdf' &&
      !file.name.toLowerCase().endsWith('.pdf')
    ) {
      setUploadError('Choose a PDF file.')
      return
    }
    setUploadProgress(0)
    try {
      const response = await uploadDocument(file, setUploadProgress)
      setRun(response.ingestion_run)
      if (response.duplicate) {
        setUploadNotice(
          `Already in your library: ${response.document.filename}. Reusing the existing document.`,
        )
      }
      await queryClient.invalidateQueries({ queryKey: ['documents'] })
    } catch (error) {
      setUploadError(errorMessage(error))
    } finally {
      setUploadProgress(null)
    }
  }

  const deleteUpload = async (document: PolicyDocument) => {
    if (
      !window.confirm(
        `Delete “${document.title}”? This removes the PDF and its indexed content from your library.`,
      )
    ) {
      return
    }
    setDeletingId(document.id)
    setUploadError(null)
    setUploadNotice(null)
    try {
      await api.deleteDocument(document.id)
      setUploadNotice(`Deleted ${document.title}.`)
      await queryClient.invalidateQueries({ queryKey: ['documents'] })
    } catch (error) {
      setUploadError(errorMessage(error))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <section
      className="panel documents-panel"
      aria-labelledby="documents-title"
    >
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Knowledge base</p>
          <h2 id="documents-title">Documents</h2>
        </div>
        <span className="count-badge">{documents.data?.length ?? 0}</span>
      </div>

      <button
        className={`drop-zone ${dragging ? 'is-dragging' : ''}`}
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragEnter={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setDragging(false)
          void handleFile(event.dataTransfer.files[0])
        }}
      >
        <span className="upload-icon" aria-hidden="true">
          ↑
        </span>
        <strong>Upload PDF</strong>
      </button>
      <input
        aria-label="Upload a policy PDF"
        ref={inputRef}
        className="visually-hidden"
        type="file"
        accept="application/pdf,.pdf"
        onChange={(event) => void handleFile(event.target.files?.[0])}
      />

      {uploadProgress !== null && (
        <div className="progress-block" aria-live="polite">
          <div className="progress-label">
            <span>Uploading</span>
            <span>{uploadProgress}%</span>
          </div>
          <progress value={uploadProgress} max="100" />
        </div>
      )}
      {run && run.status !== 'ready' && run.status !== 'failed' && (
        <p className="inline-status" aria-live="polite">
          <span className="spinner" aria-hidden="true" />{' '}
          {run.stage || 'Indexing document'}
        </p>
      )}
      {uploadNotice && (
        <p className="inline-status" aria-live="polite">
          {uploadNotice}
        </p>
      )}
      {(uploadError || run?.error) && (
        <p className="inline-error" role="alert">
          {uploadError ?? run?.error}
        </p>
      )}

      <div className="document-list" aria-live="polite">
        {documents.isLoading && <DocumentSkeleton />}
        {documents.isError && (
          <div className="empty-state error-state">
            <strong>Documents unavailable</strong>
            <span>{errorMessage(documents.error)}</span>
            <button
              type="button"
              className="text-button"
              onClick={() => void documents.refetch()}
            >
              Try again
            </button>
          </div>
        )}
        {documents.data?.length === 0 && (
          <div className="empty-state">
            <strong>No documents yet</strong>
            <span>Upload a PDF to start asking questions.</span>
          </div>
        )}
        {FOLDERS.map((folder) => {
          const items = (documents.data ?? []).filter(
            (document) => folderOf(document.source) === folder.key,
          )
          if (items.length === 0) return null
          return (
            <details
              className="doc-folder"
              key={folder.key}
              open={!closedFolders.includes(folder.key)}
              onToggle={(event) =>
                setFolderOpen(folder.key, event.currentTarget.open)
              }
            >
              <summary>
                <span className="folder-name">{folder.label}</span>
                <span className="folder-count">{items.length}</span>
              </summary>
              {items.map((document) => (
                <article className="document-card" key={document.id}>
                  <div className="pdf-mark" aria-hidden="true">
                    PDF
                  </div>
                  <div className="document-details">
                    <strong title={document.title}>{document.title}</strong>
                    <span>
                      {document.page_count}{' '}
                      {document.page_count === 1 ? 'page' : 'pages'}
                    </span>
                    {document.status !== 'ready' && (
                      <span className="document-status">
                        <StatusDot status={document.status} />
                        {document.status}
                      </span>
                    )}
                    {document.error && (
                      <span className="document-error">{document.error}</span>
                    )}
                  </div>
                  {onView && document.status === 'ready' && (
                    <button
                      className="doc-view"
                      type="button"
                      onClick={() => onView(document)}
                      aria-label={`View the PDF: ${document.title}`}
                    >
                      View
                    </button>
                  )}
                  {document.source === 'uploaded' && (
                    <button
                      className="doc-delete"
                      type="button"
                      onClick={() => void deleteUpload(document)}
                      disabled={deletingId === document.id}
                      aria-label={`Delete the PDF: ${document.title}`}
                    >
                      {deletingId === document.id ? 'Deleting' : 'Delete'}
                    </button>
                  )}
                </article>
              ))}
            </details>
          )
        })}
      </div>
    </section>
  )
}

const FOLDERS = [
  { key: 'policies', label: 'University policies' },
  { key: 'reference', label: 'Public references (NIST)' },
  { key: 'uploads', label: 'Your uploads' },
] as const

function folderOf(source: string | undefined) {
  if (source === 'reference') return 'reference'
  if (source === 'bundled') return 'policies'
  return 'uploads'
}

function DocumentSkeleton() {
  return (
    <div className="document-card skeleton-card" aria-label="Loading documents">
      <div className="skeleton square" />
      <div className="document-details">
        <span className="skeleton line wide" />
        <span className="skeleton line" />
      </div>
    </div>
  )
}
