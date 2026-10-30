import { useEffect, useRef, useState } from 'react'

interface AccountMenuProps {
  name: string | null
  email: string | null
  onSignOut: () => void
}

export function AccountMenu({ name, email, onSignOut }: AccountMenuProps) {
  const [open, setOpen] = useState(false)
  const wrap = useRef<HTMLDivElement>(null)
  const label = name || email || 'Account'

  useEffect(() => {
    if (!open) return
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent && event.key !== 'Escape') return
      if (
        event instanceof MouseEvent &&
        wrap.current?.contains(event.target as Node)
      )
        return
      setOpen(false)
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', close)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', close)
    }
  }, [open])

  return (
    <div className="account-menu" ref={wrap}>
      <button
        type="button"
        className="account-button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Account menu for ${label}`}
        onClick={() => setOpen(!open)}
      >
        {label.charAt(0).toUpperCase()}
      </button>
      {open && (
        <div className="account-popover" role="menu">
          <strong>{name ?? 'Signed in'}</strong>
          {email && <span>{email}</span>}
          <button type="button" role="menuitem" onClick={onSignOut}>
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}
