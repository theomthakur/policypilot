import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  api,
  ApiError,
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
import { PdfViewer, type ViewerTarget } from './components/PdfViewer'
import { PasscodeDialog } from './components/PasscodeDialog'
import { SignInScreen } from './components/SignInScreen'
import { AccountMenu } from './components/AccountMenu'
import { failureAnswer } from './api/failure'
import { newId } from './api/ids'
import { systemTheme, usePreference } from './hooks/usePreference'
import { AnimatedMark } from './components/AnimatedMark'
import { PolicyPilotMark } from './components/PolicyPilotMark'
import { ArchitecturePage } from './components/ArchitecturePage'
import { PresentationPage } from './components/PresentationPage'
import { TracePanel } from './components/TracePanel'
import { useTurnStream } from './hooks/useTurnStream'

const SESSION_KEY = 'policypilot_session_id'
type MobilePanel = 'documents' | 'conversation' | 'trace'
function describeRun(
  mode: 'agent' | 'baseline',
  searches: number,
  asked: boolean,
): string {
  if (asked) return 'Agent · asked you a question'
  if (mode === 'baseline') return 'Quick mode · 1 search'
  if (searches === 0) return 'Agent · replied without searching'
  return `Agent · ${searches} search${searches === 1 ? '' : 'es'}`
}

type AppView = 'workspace' | 'architecture' | 'presentation'

function viewFromHash(): AppView {
  const hash = window.location.hash.slice(1)
  return hash === 'architecture' || hash === 'presentation' ? hash : 'workspace'
}

function CollapseBar({
  side,
  label,
  count,
  open,
  onToggle,
}: {
  side: 'left' | 'right'
  label: string
  count?: number
  open: boolean
  onToggle: () => void
}) {
  // The arrow points the way the panel will move: toward its own edge to hide, away to show.
  const arrow = (side === 'left') === open ? '‹' : '›'
  return (
    <button
      type="button"
      className={`collapse-bar${open ? '' : ' is-collapsed'}`}
      aria-expanded={open}
      aria-label={`${open ? 'Hide' : 'Show'} ${label.toLowerCase()}`}
      title={`${open ? 'Hide' : 'Show'} ${label.toLowerCase()}`}
      onClick={onToggle}
    >
      <span className="collapse-arrow" aria-hidden="true">
        {arrow}
      </span>
      <span className="collapse-label">
        {label}
        {count ? <em>{count}</em> : null}
      </span>
    </button>
  )
}

export function App() {
  const queryClient = useQueryClient()
  const [launching, setLaunching] = useState(true)
  const [sessionId, setSessionId] = useState<string | null>(() =>
    localStorage.getItem(SESSION_KEY),
  )
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [activeTurnId, setActiveTurnId] = useState<string | null>(null)
  const [chosenMode, setMode] = useState<'agent' | 'baseline'>('agent')
  const [citation, setCitation] = useState<Citation | null>(null)
  const [viewer, setViewer] = useState<ViewerTarget | null>(null)
  // Panels always start visible: hiding one is a temporary choice and is never remembered.
  const [showDocuments, setShowDocuments] = useState(true)
  const [showTrace, setShowTrace] = useState(true)
  const [authRequired, setAuthRequired] = useState(false)
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>('conversation')
  const [appView, setAppView] = useState<AppView>(viewFromHash)
  const [sendError, setSendError] = useState<string | null>(null)
  const creatingSession = useRef(false)
  const completedTurn = useRef<string | null>(null)
  const clarificationTurn = useRef<string | null>(null)
  const sentMode = useRef<'agent' | 'baseline'>('agent')
  const [developer, setDeveloper] = usePreference<boolean>(
    'pp_developer',
    false,
  )
  const [theme, setTheme] = usePreference<'light' | 'dark'>(
    'pp_theme',
    systemTheme(),
  )
  const mode = developer ? chosenMode : 'agent'

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

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

  useEffect(() => {
    const syncView = () => setAppView(viewFromHash())
    window.addEventListener('hashchange', syncView)
    return () => window.removeEventListener('hashchange', syncView)
  }, [])

  const navigateTo = (view: AppView) => {
    setAppView(view)
    const nextUrl =
      view === 'workspace'
        ? `${window.location.pathname}${window.location.search}`
        : `#${view}`
    window.history.replaceState(null, '', nextUrl)
  }

  const auth = useQuery({
    queryKey: ['auth'],
    queryFn: api.getAuthState,
    retry: false,
    staleTime: Infinity,
  })
  const needsSignIn =
    auth.data?.mode !== undefined &&
    auth.data.mode !== 'off' &&
    !auth.data.authenticated
  const [signInEnded, setSignInEnded] = useState(false)

  useEffect(() => {
    const ended = () => {
      setSignInEnded(true)
      void queryClient.invalidateQueries({ queryKey: ['auth'] })
    }
    window.addEventListener('policypilot:signin-required', ended)
    return () =>
      window.removeEventListener('policypilot:signin-required', ended)
  }, [queryClient])

  const signOut = async () => {
    await api.logout()
    localStorage.removeItem(SESSION_KEY)
    setSessionId(null)
    setMessages([])
    setActiveTurnId(null)
    queryClient.clear()
    await queryClient.invalidateQueries({ queryKey: ['auth'] })
    window.location.assign('/')
  }

  const health = useQuery({
    queryKey: ['health'],
    queryFn: api.healthReady,
    refetchInterval: 30_000,
    retry: false,
  })

  const session = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => api.getSession(sessionId!),
    enabled: Boolean(sessionId) && !needsSignIn,
    retry: false,
  })

  const turn = useTurnStream(activeTurnId)
  const busy = turn.status === 'streaming' || turn.status === 'polling'

  const latestOwned = auth.data?.latest_session_id ?? null
  const createSession = useCallback(
    async (forceNew = false) => {
      if (creatingSession.current) return
      creatingSession.current = true
      try {
        // After signing in again, pick the last conversation back up instead of starting an empty one.
        const response =
          !forceNew && latestOwned
            ? await api.resumeSession(latestOwned)
            : await api.createSession()
        localStorage.setItem(SESSION_KEY, response.session_id)
        setSessionId(response.session_id)
        setMessages([])
        setActiveTurnId(null)
        completedTurn.current = null
        void queryClient.invalidateQueries({
          queryKey: ['session', response.session_id],
        })
        // Private uploads are listed per conversation, so the list changes when the conversation does.
        void queryClient.invalidateQueries({ queryKey: ['documents'] })
      } finally {
        creatingSession.current = false
      }
    },
    [latestOwned, queryClient],
  )

  useEffect(() => {
    const requireAuth = () => setAuthRequired(true)
    window.addEventListener('policypilot:auth-required', requireAuth)
    return () =>
      window.removeEventListener('policypilot:auth-required', requireAuth)
  }, [])

  const authReady = auth.isFetched && !needsSignIn
  useEffect(() => {
    if (authReady && !sessionId && !authRequired)
      void createSession().catch(() => undefined)
  }, [authReady, authRequired, createSession, sessionId])

  // A saved session id can outlive its cookie or database; start a fresh session instead of failing forever.
  useEffect(() => {
    if (session.error instanceof ApiError && session.error.status === 404)
      void createSession().catch(() => undefined)
  }, [createSession, session.error])

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
    // A failed turn still gets a reply in the chat; silence made people send the same question again.
    const failed = turn.status === 'failed'
    if (
      !activeTurnId ||
      completedTurn.current === activeTurnId ||
      !(failed || (turn.status === 'completed' && turn.answer))
    )
      return
    const answer = failed ? failureAnswer(turn.answer) : turn.answer!
    completedTurn.current = activeTurnId
    clarificationTurn.current = answer.clarification ? activeTurnId : null
    const meta = describeRun(
      sentMode.current,
      turn.totals?.tool_calls ?? 0,
      Boolean(answer.clarification),
    )
    setMessages((current) => [
      ...current,
      { id: `assistant-${activeTurnId}`, role: 'assistant', answer, meta },
    ])
  }, [activeTurnId, turn.answer, turn.status, turn.totals])

  const sendMessage = async (content: string, replyToClarification = false) => {
    if (!sessionId || busy) return
    setSendError(null)
    setMessages((current) => [
      ...current,
      { id: `user-${newId()}`, role: 'user', text: content },
    ])
    sentMode.current = mode
    try {
      const response = await api.sendMessage(
        sessionId,
        content,
        mode,
        replyToClarification ? clarificationTurn.current : null,
      )
      clarificationTurn.current = null
      completedTurn.current = null
      setActiveTurnId(response.turn_id)
      setMobilePanel('conversation')
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        void createSession().catch(() => undefined)
        setSendError(
          'Your session expired, so a new one was started. Please send your message again.',
        )
      } else {
        setSendError(errorMessage(error))
      }
      setMessages((current) => current.slice(0, -1))
    }
  }

  const resetSession = async () => {
    localStorage.removeItem(SESSION_KEY)
    setSessionId(null)
    setMessages([])
    setActiveTurnId(null)
    await createSession(true)
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
    turn.events.filter((event) => !event.hidden).at(-1)?.summary ??
    (mode === 'baseline' ? 'Running one-pass retrieval…' : null)
  const degraded = health.data?.status === 'degraded'

  if (needsSignIn && !launching) {
    const failed = new URLSearchParams(window.location.search).has('auth_error')
    return (
      <div className="app-shell">
        <SignInScreen
          reason={signInEnded ? 'expired' : failed ? 'failed' : 'first'}
        />
      </div>
    )
  }

  return (
    <div className="app-shell">
      {launching && (
        <div
          className="launch-screen"
          role="status"
          aria-label="Loading PolicyPilot"
        >
          <div className="launch-brand">
            <div className="launch-logo" aria-hidden="true">
              <AnimatedMark className="launch-mark" speed={1.1} />
            </div>
            <div className="launch-wordmark">PolicyPilot</div>
            <p>Preparing your evidence workspace</p>
            <span className="launch-progress" />
          </div>
        </div>
      )}
      <header className="topbar">
        <h1 className="visually-hidden">PolicyPilot, a policy assistant</h1>
        <div className="brand">
          <PolicyPilotMark className="header-mark" />
          <div>
            <strong>PolicyPilot</strong>
            <span>Research, AI and learning policy assistant</span>
          </div>
        </div>
        <nav className="primary-nav" aria-label="Application sections">
          {(
            [
              ['workspace', 'Workspace'],
              ['architecture', 'System design'],
              ['presentation', 'Presentation'],
            ] as const
          ).map(([view, label]) => (
            <button
              key={view}
              type="button"
              className={appView === view ? 'active' : ''}
              aria-current={appView === view ? 'page' : undefined}
              onClick={() => navigateTo(view)}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="topbar-actions">
          <span
            className={`health-pill health-${health.data?.status ?? (health.isError ? 'down' : 'checking')}${developer || health.data?.status !== 'ok' ? '' : ' is-quiet'}`}
            aria-hidden={!(developer || health.data?.status !== 'ok')}
          >
            <span />
            {health.data?.status ?? (health.isError ? 'offline' : 'checking')}
          </span>
          <button
            className={`switch${developer ? ' on' : ''}`}
            type="button"
            role="switch"
            aria-checked={developer}
            title="Show metrics, technical details and the Agent / Quick switch"
            onClick={() => setDeveloper(!developer)}
          >
            <span className="switch-track" aria-hidden="true">
              <i />
            </span>
            Developer
          </button>
          <button
            className="icon-button"
            type="button"
            aria-label={
              theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'
            }
            title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            {theme === 'dark' ? '☀' : '☾'}
          </button>
          {auth.data?.user && (
            <AccountMenu
              name={auth.data.user.name}
              email={auth.data.user.email}
              onSignOut={() => void signOut()}
            />
          )}
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

      {appView === 'workspace' ? (
        <>
          <nav className="mobile-tabs" aria-label="Workspace panels">
            {(['documents', 'conversation', 'trace'] as MobilePanel[]).map(
              (panel) => (
                <button
                  key={panel}
                  className={mobilePanel === panel ? 'active' : ''}
                  type="button"
                  onClick={() => {
                    setMobilePanel(panel)
                    if (panel === 'documents') setShowDocuments(true)
                    if (panel === 'trace') setShowTrace(true)
                  }}
                >
                  {panel}
                  {panel === 'trace' && turn.events.length > 0 && (
                    <span>{turn.events.length}</span>
                  )}
                </button>
              ),
            )}
          </nav>

          <main
            className={`workspace${showDocuments ? '' : ' no-documents'}${showTrace ? '' : ' no-trace'}`}
          >
            <aside
              className={`workspace-pane pane-documents ${mobilePanel === 'documents' ? 'mobile-active' : ''}`}
              aria-label="Knowledge base"
            >
              <CollapseBar
                side="left"
                label="Knowledge base"
                open={showDocuments}
                onToggle={() => setShowDocuments(!showDocuments)}
              />
              <div className="pane-body" hidden={!showDocuments}>
                <DocumentsPanel
                  onView={(document) =>
                    setViewer({ id: document.id, title: document.title })
                  }
                />
              </div>
            </aside>
            <div
              className={`workspace-pane pane-conversation ${mobilePanel === 'conversation' ? 'mobile-active' : ''}`}
            >
              <ConversationPanel
                messages={messages}
                busy={busy}
                streamLabel={streamLabel}
                sessionReady={Boolean(sessionId)}
                mode={mode}
                developer={developer}
                onModeChange={setMode}
                onSend={(content, reply) => void sendMessage(content, reply)}
                onCitationOpen={setCitation}
              />
            </div>
            <aside
              className={`workspace-pane pane-trace ${mobilePanel === 'trace' ? 'mobile-active' : ''}`}
              aria-label="Agent activity"
            >
              <CollapseBar
                side="right"
                label="Agent activity"
                count={turn.events.length}
                open={showTrace}
                onToggle={() => setShowTrace(!showTrace)}
              />
              <div className="pane-body" hidden={!showTrace}>
                <TracePanel
                  events={turn.events}
                  totals={turn.totals}
                  streamStatus={turn.status}
                  developer={developer}
                />
              </div>
            </aside>
          </main>
        </>
      ) : appView === 'architecture' ? (
        <ArchitecturePage onBack={() => navigateTo('workspace')} />
      ) : (
        <PresentationPage onBack={() => navigateTo('workspace')} />
      )}

      <CitationDrawer
        citation={citation}
        onClose={() => setCitation(null)}
        onViewPdf={(item) => {
          setCitation(null)
          setViewer({
            id: item.document_id,
            title: item.document_title,
            page: item.page,
          })
        }}
      />
      <PdfViewer target={viewer} onClose={() => setViewer(null)} />
      <PasscodeDialog open={authRequired} onSubmit={submitPasscode} />
    </div>
  )
}
