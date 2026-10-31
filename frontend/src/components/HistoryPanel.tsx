import { CloseIcon } from './CloseIcon'

export interface HistoryItem {
  id: string
  title: string
  at: number
}

interface HistoryPanelProps {
  items: HistoryItem[]
  currentId: string | null
  disabled: boolean
  onOpen: (id: string) => void
  onDelete: (id: string) => void
  onClear: () => void
}

function when(at: number): string {
  const days = Math.floor((Date.now() - at) / 86_400_000)
  if (days <= 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`
  return new Date(at).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
}

export function HistoryPanel({
  items,
  currentId,
  disabled,
  onOpen,
  onDelete,
  onClear,
}: HistoryPanelProps) {
  if (items.length === 0) {
    return (
      <p className="history-empty">
        Your conversations will appear here once you ask a question.
      </p>
    )
  }
  let lastLabel = ''
  return (
    <>
      <div className="history-actions">
        <button
          type="button"
          className="history-clear"
          disabled={disabled}
          onClick={onClear}
        >
          Clear history
        </button>
      </div>
      <ul className="history-list">
        {items.map((item) => {
          const label = when(item.at)
          const heading = label !== lastLabel
          lastLabel = label
          return (
            <li key={item.id}>
              {heading && <span className="history-group">{label}</span>}
              <div
                className={`history-item${item.id === currentId ? ' active' : ''}`}
              >
                <button
                  type="button"
                  className="history-open"
                  title={item.title}
                  disabled={disabled}
                  onClick={() => onOpen(item.id)}
                >
                  {item.title}
                </button>
                <button
                  type="button"
                  className="history-delete"
                  aria-label={`Remove "${item.title}" from history`}
                  title="Remove from history"
                  onClick={() => onDelete(item.id)}
                >
                  <CloseIcon size={12} />
                </button>
              </div>
            </li>
          )
        })}
      </ul>
    </>
  )
}
