import { PolicyPilotMark } from './PolicyPilotMark'

interface SignInScreenProps {
  /** Why the person is here: first visit, a failed attempt, or a login that ended. */
  reason: 'first' | 'failed' | 'expired'
}

const copy = {
  first:
    'Sign in with your university account to ask questions about the policies.',
  failed: 'That sign-in did not work. Please try again.',
  expired: 'Your sign-in ended. Please sign in again to continue.',
}

export function SignInScreen({ reason }: SignInScreenProps) {
  return (
    <main className="signin-screen">
      <div className="signin-card">
        <PolicyPilotMark className="passcode-mark" />
        <h1>PolicyPilot</h1>
        <p role={reason === 'first' ? undefined : 'alert'}>{copy[reason]}</p>
        <a className="signin-button" href="/api/v1/auth/login">
          Sign in
        </a>
      </div>
    </main>
  )
}
