import { useState } from 'react'
import { PolicyPilotMark } from './PolicyPilotMark'

interface PasscodeDialogProps {
  open: boolean
  onSubmit: (passcode: string) => Promise<void>
}

export function PasscodeDialog({ open, onSubmit }: PasscodeDialogProps) {
  const [passcode, setPasscode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (!open) return null

  return (
    <div className="passcode-layer">
      <form
        className="passcode-card"
        onSubmit={async (event) => {
          event.preventDefault()
          if (!passcode.trim()) return
          setSubmitting(true)
          setError(null)
          try {
            await onSubmit(passcode)
          } catch (submitError) {
            setError(
              submitError instanceof Error
                ? submitError.message
                : 'Access code was not accepted.',
            )
          } finally {
            setSubmitting(false)
          }
        }}
      >
        <PolicyPilotMark className="passcode-mark" />
        <p className="eyebrow">Protected demonstration</p>
        <h1>Enter the access code</h1>
        <p>This public demo is gated to control model usage and cost.</p>
        <label htmlFor="passcode">Access code</label>
        <input
          id="passcode"
          type="password"
          autoComplete="current-password"
          autoFocus
          value={passcode}
          onChange={(event) => setPasscode(event.target.value)}
        />
        {error && (
          <p className="inline-error" role="alert">
            {error}
          </p>
        )}
        <button
          className="primary-button"
          type="submit"
          disabled={submitting || !passcode.trim()}
        >
          {submitting ? 'Checking…' : 'Open PolicyPilot'}
        </button>
      </form>
    </div>
  )
}
