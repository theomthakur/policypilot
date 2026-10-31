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
import { HistoryPanel, type HistoryItem } from './components/HistoryPanel'
import { DocumentsPanel } from './components/DocumentsPanel'
import { PdfViewer, type ViewerTarget } from './components/PdfViewer'
import { PasscodeDialog } from './components/PasscodeDialog'
import { SignInScreen } from './components/SignInScreen'
import { AccountMenu } from './components/AccountMenu'
import { failureAnswer } from './api/failure'
import { newId } from './api/ids'
import { usePreference } from './hooks/usePreference'
import { AnimatedMark } from './components/AnimatedMark'
import { PolicyPilotMark } from './components/PolicyPilotMark'
import { ArchitecturePage } from './components/ArchitecturePage'
import { PresentationPage } from './components/PresentationPage'
import { TracePanel } from './components/TracePanel'
import { useTurnStream } from './hooks/useTurnStream'

const SESSION_KEY = 'policypilot_session_id'
const HISTORY_KEY = 'pp_session_history'

function readHistory(): HistoryItem[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(HISTORY_KEY) ?? '[]')
    return Array.isArray(parsed) ? parsed.slice(0, 50) : []
  } catch {
    return []
  }
}

function saveHistory(items: HistoryItem[]) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, 50)))
  } catch {
    // History is a convenience; the conversation itself is stored on the server.
  }
}
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

function IconBook() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5z" />
      <path d="M4 5.5v16M9 8h7" />
    </svg>
  )
}

function IconActivity() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 12h4l3-8 4 16 3-8h4" />
    </svg>
  )
}

function IconClock() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  )
}

function IconLogout() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3" />
      <path d="M16 8l4 4-4 4M20 12H9" />
    </svg>
  )
}

function IconSidebar() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="4" width="18" height="16" rx="3" />
      <path d="M9 4v16" />
    </svg>
  )
}

function IconSun() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  )
}

function IconMoon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />
    </svg>
  )
}

function IconPlus() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}

function IconDiagram() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
      <path d="M10 6.5h4a3 3 0 0 1 3 3V14" />
    </svg>
  )
}

function IconSlides() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="4" width="18" height="12" rx="2" />
      <path d="M12 16v4M8 20h8" />
    </svg>
  )
}

function IconCode() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M8 7l-5 5 5 5M16 7l5 5-5 5M14 4l-4 16" />
    </svg>
  )
}

function ThemeIcon({ theme }: { theme: 'light' | 'dark' }) {
  return theme === 'dark' ? <IconSun /> : <IconMoon />
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
  const [showSidebar, setShowSidebar] = useState(true)
  const [sidebarTab, setSidebarTab] = useState<
    'documents' | 'activity' | 'history'
  >('documents')
  const [history, setHistory] = useState<HistoryItem[]>(readHistory)
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
  const [theme, setTheme] = usePreference<'light' | 'dark'>('pp_theme', 'light')
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
  const firstName = auth.data?.user?.name ?? null
  const [signInEnded, setSignInEnded] = useState(false)
  // "Your sign-in ended" is only true for someone who had signed in during this visit; a first visit also
  // gets a 401 from the requests that start before the sign-in state is known, and that must not say so.
  const wasSignedIn = useRef(false)
  useEffect(() => {
    if (auth.data?.authenticated) wasSignedIn.current = true
  }, [auth.data?.authenticated])

  useEffect(() => {
    const ended = () => {
      if (wasSignedIn.current) setSignInEnded(true)
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
        // Personal uploads follow the signed-in person across conversations; refresh after switching chats.
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
    if (session.error instanceof ApiError && session.error.status === 404) {
      if (sessionId) {
        setHistory((current) => {
          const next = current.filter((item) => item.id !== sessionId)
          saveHistory(next)
          return next
        })
      }
      void createSession().catch(() => undefined)
    }
  }, [createSession, session.error, sessionId])

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

  const recordHistory = (id: string, question: string) => {
    setHistory((current) => {
      const existing = current.find((item) => item.id === id)
      const title =
        existing?.title ?? question.replace(/\s+/g, ' ').slice(0, 70)
      const next = [
        { id, title, at: Date.now() },
        ...current.filter((item) => item.id !== id),
      ]
      saveHistory(next)
      return next
    })
  }

  const removeHistory = (id: string) => {
    setHistory((current) => {
      const next = current.filter((item) => item.id !== id)
      saveHistory(next)
      return next
    })
  }

  const openSession = async (id: string) => {
    navigateTo('workspace')
    if (busy || id === sessionId) return
    try {
      await api.resumeSession(id)
    } catch {
      removeHistory(id)
      setSendError('That conversation is no longer available.')
      return
    }
    setSendError(null)
    localStorage.setItem(SESSION_KEY, id)
    setSessionId(id)
    setMessages([])
    setActiveTurnId(null)
    completedTurn.current = null
    clarificationTurn.current = null
    void queryClient.invalidateQueries({ queryKey: ['session', id] })
    void queryClient.invalidateQueries({ queryKey: ['documents'] })
  }

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
      recordHistory(sessionId, content)
      setMobilePanel('conversation')
      setSidebarTab('activity')
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

  const sidebar = (
    <aside
      className={`workspace-pane pane-sidebar${showSidebar ? '' : ' is-collapsed'} ${mobilePanel !== 'conversation' ? 'mobile-active' : ''}`}
      aria-label="Workspace sidebar"
    >
      <div className="sidebar-head">
        <button
          type="button"
          className="sidebar-logo"
          aria-label={showSidebar ? 'Collapse sidebar' : 'Expand sidebar'}
          aria-expanded={showSidebar}
          title={showSidebar ? 'Collapse sidebar' : 'Expand sidebar'}
          onClick={() => setShowSidebar(!showSidebar)}
        >
          <PolicyPilotMark className="sidebar-mark" />
        </button>
        <span className="sidebar-name">PolicyPilot</span>
        <button
          type="button"
          className="sidebar-toggle"
          aria-label="Collapse sidebar"
          title="Collapse sidebar"
          onClick={() => setShowSidebar(false)}
          tabIndex={showSidebar ? 0 : -1}
        >
          <IconSidebar />
        </button>
      </div>
      <button
        type="button"
        className="sidebar-new"
        title="New session"
        aria-label="New session"
        onClick={() => {
          navigateTo('workspace')
          void resetSession()
        }}
        disabled={busy}
      >
        <IconPlus />
        <span className="nav-label">New session</span>
      </button>
      <div className="sidebar-pages">
        <button
          type="button"
          className="sidebar-link"
          title="System design"
          onClick={() => navigateTo('architecture')}
        >
          <IconDiagram />
          <span className="nav-label">System design</span>
        </button>
        <button
          type="button"
          className="sidebar-link"
          title="Presentation"
          onClick={() => navigateTo('presentation')}
        >
          <IconSlides />
          <span className="nav-label">Presentation</span>
        </button>
      </div>
      <div className="sidebar-nav" role="tablist">
        {(
          [
            ['documents', 'Knowledge base', <IconBook key="b" />],
            ['activity', 'Agent activity', <IconActivity key="a" />],
            ['history', 'History', <IconClock key="h" />],
          ] as const
        ).map(([key, label, icon]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={sidebarTab === key && appView === 'workspace'}
            aria-label={label}
            title={label}
            className={
              sidebarTab === key && appView === 'workspace' ? 'active' : ''
            }
            onClick={() => {
              setSidebarTab(key)
              setShowSidebar(true)
              navigateTo('workspace')
            }}
          >
            {icon}
            <span className="nav-label">{label}</span>
            {key === 'activity' && turn.events.length > 0 && (
              <span className="tab-count">{turn.events.length}</span>
            )}
          </button>
        ))}
      </div>
      <div
        className="sidebar-content"
        hidden={!showSidebar || appView !== 'workspace'}
      >
        {sidebarTab === 'history' ? (
          <HistoryPanel
            items={history}
            currentId={sessionId}
            disabled={busy}
            onOpen={(id) => void openSession(id)}
            onDelete={removeHistory}
          />
        ) : sidebarTab === 'documents' ? (
          <DocumentsPanel
            onView={(document) =>
              setViewer({ id: document.id, title: document.title })
            }
          />
        ) : (
          <TracePanel
            events={turn.events}
            totals={turn.totals}
            streamStatus={turn.status}
            developer={developer}
          />
        )}
      </div>
      <div className="sidebar-footer">
        <div className="sidebar-tools">
          <button
            type="button"
            className={`tool-button${developer ? ' on' : ''}`}
            aria-pressed={developer}
            aria-label="Developer mode"
            title="Developer mode: metrics, technical details and the Agent / Quick switch"
            onClick={() => setDeveloper(!developer)}
          >
            <IconCode />
          </button>
          <button
            type="button"
            className="tool-button"
            aria-label={
              theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'
            }
            title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            <ThemeIcon theme={theme} />
          </button>
          {auth.data?.user && (
            <>
              <span
                className="tool-avatar"
                title={[auth.data.user.name, auth.data.user.email]
                  .filter(Boolean)
                  .join(' · ')}
                role="img"
                aria-label={`Signed in as ${auth.data.user.name ?? auth.data.user.email ?? 'you'}`}
              >
                {(auth.data.user.name || auth.data.user.email || 'A')
                  .charAt(0)
                  .toUpperCase()}
              </span>
              <button
                type="button"
                className="tool-button"
                aria-label="Sign out"
                title="Sign out"
                onClick={() => void signOut()}
              >
                <IconLogout />
              </button>
            </>
          )}
        </div>
      </div>
    </aside>
  )

  return (
    <div className={`app-shell view-${appView}`}>
      {launching && (
        <div
          className="launch-screen"
          role="status"
          aria-label="Loading PolicyPilot"
        >
          <div className="launch-brand">
            <div className="launch-logo" aria-hidden="true">
              <AnimatedMark className="launch-mark" speed={1.6} shine />
            </div>
            <div className="launch-wordmark">PolicyPilot</div>
          </div>
        </div>
      )}
      <header className="topbar">
        <h1 className="visually-hidden">PolicyPilot, a policy assistant</h1>
        <div className="brand">
          <PolicyPilotMark className="header-mark" />
          <strong>PolicyPilot</strong>
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
            <ThemeIcon theme={theme} />
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
                    if (panel === 'documents') setSidebarTab('documents')
                    if (panel === 'trace') setSidebarTab('activity')
                    if (panel !== 'conversation') setShowSidebar(true)
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

          <main className={`workspace${showSidebar ? '' : ' no-sidebar'}`}>
            {sidebar}
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
                firstName={firstName}
                onModeChange={setMode}
                onSend={(content, reply) => void sendMessage(content, reply)}
                onCitationOpen={setCitation}
              />
            </div>
          </main>
        </>
      ) : (
        <div className={`workspace${showSidebar ? '' : ' no-sidebar'}`}>
          {sidebar}
          <div className="workspace-pane pane-page mobile-active">
            {appView === 'architecture' ? (
              <ArchitecturePage onBack={() => navigateTo('workspace')} />
            ) : (
              <PresentationPage onBack={() => navigateTo('workspace')} />
            )}
          </div>
        </div>
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
