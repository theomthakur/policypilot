import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  api,
  clearDemoPasscode,
  errorMessage,
  setDemoPasscode,
} from './api/client'
import type { Citation } from './api/types'
import { CitationDrawer } from './components/CitationDrawer'
import {
  ConversationPanel,
  type DisplayMessage,
} from './components/ConversationPanel'
import { DocumentsPanel } from './components/DocumentsPanel'
import { PasscodeDialog } from './components/PasscodeDialog'
import { PolicyPilotMark } from './components/PolicyPilotMark'
import { TracePanel } from './components/TracePanel'
import { useTurnStream } from './hooks/useTurnStream'

const SESSION_KEY = 'policypilot_session_id'
type MobilePanel = 'documents' | 'conversation' | 'trace'

export function App() {
  const queryClient = useQueryClient()
  const [launching, setLaunching] = useState(true)
  const [sessionId, setSessionId] = useState<string | null>(() =>
    localStorage.getItem(SESSION_KEY),
  )
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [activeTurnId, setActiveTurnId] = useState<string | null>(null)
  const [mode, setMode] = useState<'agent' | 'baseline'>('agent')
  const [citation, setCitation] = useState<Citation | null>(null)
  const [authRequired, setAuthRequired] = useState(false)
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>('conversation')
  const [sendError, setSendError] = useState<string | null>(null)
  const creatingSession = useRef(false)
  const completedTurn = useRef<string | null>(null)

  useEffect(() => {
    const reduceMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches
    const timer = window.setTimeout(
      () => setLaunching(false),
      reduceMotion ? 120 : 1150,
    )
    return () => window.clearTimeout(timer)
  }, [])

  const health = useQuery({
    queryKey: ['health'],
    queryFn: api.healthReady,
    refetchInterval: 30_000,
    retry: false,
  })

  const session = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => api.getSession(sessionId!),
    enabled: Boolean(sessionId),
    retry: false,
  })

  const turn = useTurnStream(activeTurnId)
  const busy = turn.status === 'streaming' || turn.status === 'polling'

  const createSession = useCallback(async () => {
    if (creatingSession.current) return
    creatingSession.current = true
    try {
      const response = await api.createSession()
      localStorage.setItem(SESSION_KEY, response.session_id)
      setSessionId(response.session_id)
      setMessages([])
      setActiveTurnId(null)
      completedTurn.current = null
    } finally {
      creatingSession.current = false
    }
  }, [])

  useEffect(() => {
    const requireAuth = () => setAuthRequired(true)
    window.addEventListener('policypilot:auth-required', requireAuth)
    return () =>
      window.removeEventListener('policypilot:auth-required', requireAuth)
  }, [])

  useEffect(() => {
    if (!sessionId && !authRequired) void createSession().catch(() => undefined)
  }, [authRequired, createSession, sessionId])

  useEffect(() => {
    if (!session.data || messages.length > 0) return
    setMessages(
      session.data.turns.map((item) => ({
        id: item.id,
        role: item.role,
        text: item.content,
        answer: item.answer,
      })),
    )
  }, [messages.length, session.data])

  useEffect(() => {
    if (
      !activeTurnId ||
      !turn.answer ||
      turn.status !== 'completed' ||
      completedTurn.current === activeTurnId
    )
      return
    completedTurn.current = activeTurnId
    setMessages((current) => [
      ...current,
      {
        id: `assistant-${activeTurnId}`,
        role: 'assistant',
        answer: turn.answer,
      },
    ])
  }, [activeTurnId, turn.answer, turn.status])

  const sendMessage = async (content: string) => {
    if (!sessionId || busy) return
    setSendError(null)
    setMessages((current) => [
      ...current,
      { id: `user-${crypto.randomUUID()}`, role: 'user', text: content },
    ])
    try {
      const response = await api.sendMessage(sessionId, content, mode)
      completedTurn.current = null
      setActiveTurnId(response.turn_id)
      setMobilePanel('conversation')
    } catch (error) {
      setSendError(errorMessage(error))
      setMessages((current) => current.slice(0, -1))
    }
  }

  const resetSession = async () => {
    localStorage.removeItem(SESSION_KEY)
    setSessionId(null)
    setMessages([])
    setActiveTurnId(null)
    await createSession()
  }

  const submitPasscode = async (passcode: string) => {
    setDemoPasscode(passcode)
    try {
      await api.healthReady()
      setAuthRequired(false)
      await queryClient.invalidateQueries()
      if (!sessionId) await createSession()
    } catch (error) {
      clearDemoPasscode()
      throw error
    }
  }

  const streamLabel =
    turn.events.at(-1)?.summary ??
    (mode === 'baseline' ? 'Running one-pass retrieval…' : null)
  const degraded = health.data?.status === 'degraded'

  return (
    <div className="app-shell">
      {launching && (
        <div
          className="launch-screen"
          role="status"
          aria-label="Loading PolicyPilot"
        >
          <div className="launch-brand">
            <PolicyPilotMark className="launch-mark" />
            <div className="launch-wordmark">PolicyPilot</div>
            <p>Evidence-grounded policy intelligence</p>
          </div>
          <div className="launch-progress" aria-hidden="true">
            <span />
          </div>
        </div>
      )}
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <PolicyPilotMark />
          </div>
          <div>
            <strong>PolicyPilot</strong>
            <span>Research, AI and learning policy assistant</span>
          </div>
        </div>
        <div className="topbar-actions">
          <span
            className={`health-pill health-${health.data?.status ?? (health.isError ? 'down' : 'checking')}`}
          >
            <span />
            {health.data?.status ?? (health.isError ? 'offline' : 'checking')}
          </span>
          <button
            className="secondary-button"
            type="button"
            onClick={() => void resetSession()}
            disabled={busy}
          >
            New session
          </button>
        </div>
      </header>

      {degraded && (
        <div className="degraded-banner" role="status">
          <strong>Reduced performance:</strong> Redis is unavailable. Sessions
          remain durable and search is running without cache.
        </div>
      )}
      {health.isError && !authRequired && (
        <div className="outage-banner" role="alert">
          The API is unavailable. {errorMessage(health.error)}
        </div>
      )}
      {sendError && (
        <div className="outage-banner" role="alert">
          {sendError}
        </div>
      )}

      <nav className="mobile-tabs" aria-label="Workspace panels">
        {(['documents', 'conversation', 'trace'] as MobilePanel[]).map(
          (panel) => (
            <button
              key={panel}
              className={mobilePanel === panel ? 'active' : ''}
              type="button"
              onClick={() => setMobilePanel(panel)}
            >
              {panel}
              {panel === 'trace' && turn.events.length > 0 && (
                <span>{turn.events.length}</span>
              )}
            </button>
          ),
        )}
      </nav>

      <main className="workspace">
        <div
          className={`workspace-pane pane-documents ${mobilePanel === 'documents' ? 'mobile-active' : ''}`}
        >
          <DocumentsPanel />
        </div>
        <div
          className={`workspace-pane pane-conversation ${mobilePanel === 'conversation' ? 'mobile-active' : ''}`}
        >
          <ConversationPanel
            messages={messages}
            busy={busy}
            streamLabel={streamLabel}
            sessionReady={Boolean(sessionId)}
            mode={mode}
            onModeChange={setMode}
            onSend={(content) => void sendMessage(content)}
            onCitationOpen={setCitation}
          />
        </div>
        <div
          className={`workspace-pane pane-trace ${mobilePanel === 'trace' ? 'mobile-active' : ''}`}
        >
          <TracePanel
            events={turn.events}
            totals={turn.totals}
            streamStatus={turn.status}
          />
        </div>
      </main>

      <CitationDrawer citation={citation} onClose={() => setCitation(null)} />
      <PasscodeDialog open={authRequired} onSubmit={submitPasscode} />
    </div>
  )
}
