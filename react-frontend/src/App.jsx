import { useState, useCallback, useEffect, createContext, useContext } from 'react'
import { v4 as uuidv4 } from 'uuid'
import Sidebar from './components/Sidebar'
import HomePage from './components/HomePage'
import ResultsPage from './components/ResultsPage'
import LoginPage from './components/LoginPage'
import { streamChat, listSessions, loadSession, deleteSession } from './api/client'

export const ThemeContext = createContext()
export const useTheme = () => useContext(ThemeContext)

const SESSION_KEY = 'convergefi_session_id'

const AUTH_KEY = 'convergefi_auth'
const THEME_KEY = 'convergefi_theme'

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() =>
    sessionStorage.getItem(AUTH_KEY) === '1'
  )
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem(THEME_KEY)
    if (saved === 'dark' || saved === 'light') return saved
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })
  const [sessionId, setSessionId] = useState(() =>
    localStorage.getItem(SESSION_KEY) || uuidv4()
  )
  const [model, setModel] = useState('gpt-oss-120b')
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [sessions, setSessions] = useState([])       // sidebar session list
  const [sessionsLoading, setSessionsLoading] = useState(true)

  const handleLogin = useCallback(() => {
    sessionStorage.setItem(AUTH_KEY, '1')
    setIsAuthenticated(true)
  }, [])

  const handleLogout = useCallback(() => {
    sessionStorage.removeItem(AUTH_KEY)
    setIsAuthenticated(false)
    const newId = uuidv4()
    setSessionId(newId)
    setMessages([])
  }, [])

  // Persist sessionId to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem(SESSION_KEY, sessionId)
  }, [sessionId])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem(THEME_KEY, theme)
  }, [theme])

  const toggleTheme = useCallback((e) => {
    if (!document.startViewTransition) {
      setTheme(t => t === 'light' ? 'dark' : 'light')
      return
    }

    const x = e?.clientX ?? window.innerWidth / 2
    const y = e?.clientY ?? window.innerHeight / 2
    const endRadius = Math.hypot(
      Math.max(x, window.innerWidth - x),
      Math.max(y, window.innerHeight - y)
    )

    const transition = document.startViewTransition(() => {
      setTheme(t => t === 'light' ? 'dark' : 'light')
    })

    transition.ready.then(() => {
      document.documentElement.animate(
        {
          clipPath: [
            `circle(0px at ${x}px ${y}px)`,
            `circle(${endRadius}px at ${x}px ${y}px)`
          ]
        },
        {
          duration: 450,
          easing: 'ease-out',
          pseudoElement: '::view-transition-new(root)'
        }
      )
    })
  }, [])

  // ── Load session list from MongoDB on mount ──────────────────────────────────
  const refreshSessions = useCallback(async () => {
    setSessionsLoading(true)
    const list = await listSessions()
    setSessions(list)
    setSessionsLoading(false)
  }, [])

  useEffect(() => { refreshSessions() }, [refreshSessions])

  // ── Restore current session messages on mount ────────────────────────────────
  useEffect(() => {
    async function restore() {
      const data = await loadSession(sessionId)
      if (!data || !data.messages || data.messages.length === 0) return

      // Rebuild the UI message array from persisted messages
      const rebuilt = []
      const raw = data.messages
      for (let i = 0; i < raw.length; i++) {
        const m = raw[i]
        if (m.role === 'user') {
          rebuilt.push({ role: 'user', question: m.question })
        } else if (m.role === 'assistant') {
          rebuilt.push({
            role: 'assistant',
            answer: m.answer || '',
            citations: m.citations || [],
            artifacts: m.artifacts || [],
            steps: [],
            streaming: false,
            toolStatus: null,
          })
        }
      }
      if (rebuilt.length > 0) setMessages(rebuilt)
    }
    restore()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])  // Only on mount — restoring based on stored sessionId

  // ── Switch to a past session from sidebar ────────────────────────────────────
  const handleLoadSession = useCallback(async (id) => {
    if (id === sessionId && messages.length > 0) return  // already active
    const data = await loadSession(id)
    if (!data) return
    const rebuilt = []
    for (const m of data.messages || []) {
      if (m.role === 'user') {
        rebuilt.push({ role: 'user', question: m.question })
      } else if (m.role === 'assistant') {
        rebuilt.push({
          role: 'assistant',
          answer: m.answer || '',
          citations: m.citations || [],
          artifacts: m.artifacts || [],
          steps: [],
          streaming: false,
          toolStatus: null,
        })
      }
    }
    setSessionId(id)
    setMessages(rebuilt)
  }, [sessionId, messages.length])

  // ── New chat ──────────────────────────────────────────────────────────────────
  const handleNewChat = useCallback(() => {
    const newId = uuidv4()
    setSessionId(newId)
    setMessages([])
  }, [])

  // ── Delete a session from the sidebar ────────────────────────────────────────
  const handleDeleteSession = useCallback(async (id) => {
    await deleteSession(id)
    setSessions(prev => prev.filter(s => s.session_id !== id))
    if (id === sessionId) {
      handleNewChat()
    }
  }, [sessionId, handleNewChat])

  // ── Submit a query ────────────────────────────────────────────────────────────
  const handleSubmit = useCallback(async (question) => {
    if (!question.trim() || isLoading) return

    setMessages(prev => [
      ...prev,
      { role: 'user', question },
      { role: 'assistant', answer: '', citations: [], artifacts: [], logs: [], streaming: true, toolStatus: null, steps: [] },
    ])
    setIsLoading(true)

    const updateLast = (updater) => {
      setMessages(prev => {
        const msgs = [...prev]
        const last = msgs[msgs.length - 1]
        if (last?.role === 'assistant') {
          msgs[msgs.length - 1] = updater(last)
        }
        return msgs
      })
    }

    try {
      for await (const event of streamChat(question, sessionId, model)) {
        if (event.type === 'tool') {
          const args = event.arguments || {}
          let label = `Processing…`
          if (event.name === 'search_pages') {
            label = args.query ? `Searching census files for "${args.query}"` : 'Searching census documents'
          } else if (event.name === 'read_page') {
            const stateInfo = args.state ? ` (${args.state})` : ''
            label = args.page_number ? `Consulting page ${args.page_number}${stateInfo}` : 'Reading census documents'
          } else if (event.name === 'execute_python') {
            const code = args.code || ''
            if (code.includes('plot') || code.includes('plt.') || code.includes('savefig')) {
              label = 'Generating visual comparison chart'
            } else if (code.includes('pct_change') || code.includes('growth') || code.includes('ratio')) {
              label = 'Calculating growth statistics and census metrics'
            } else {
              label = 'Performing data calculations'
            }
          } else if (event.name === 'list_available_csvs') {
            label = 'Locating available census spreadsheets'
          } else if (event.name === 'save_artifact') {
            label = args.name ? `Creating comparison file: ${args.name}` : 'Saving spreadsheet'
          }

          updateLast(last => {
            const steps = last.steps || []
            const newSteps = [...steps]
            if (newSteps.length > 0) {
              newSteps[newSteps.length - 1] = { ...newSteps[newSteps.length - 1], status: 'done' }
            }
            newSteps.push({ label, status: 'running' })
            return { ...last, steps: newSteps, toolStatus: label }
          })
        } else if (event.type === 'chunk') {
          updateLast(last => {
            const newSteps = (last.steps || []).map(s => s.status === 'running' ? { ...s, status: 'done' } : s)
            return { ...last, answer: last.answer + event.text, steps: newSteps, toolStatus: null }
          })
        } else if (event.type === 'done') {
          updateLast(last => {
            const newSteps = (last.steps || []).map(s => s.status === 'running' ? { ...s, status: 'done' } : s)
            return {
              ...last,
              citations: event.citations ?? [],
              artifacts: event.artifacts ?? [],
              logs: event.logs ?? [],
              steps: newSteps,
              streaming: false,
              toolStatus: null,
            }
          })
          // Refresh sidebar sessions list after a completed turn
          refreshSessions()
        } else if (event.type === 'error') {
          updateLast(last => {
            const newSteps = (last.steps || []).map(s => s.status === 'running' ? { ...s, status: 'done' } : s)
            return { ...last, answer: last.answer || `**Error:** ${event.message}`, steps: newSteps, streaming: false, toolStatus: null }
          })
        }
      }
    } catch (err) {
      updateLast(last => {
        const newSteps = (last.steps || []).map(s => s.status === 'running' ? { ...s, status: 'done' } : s)
        return { ...last, answer: last.answer || `**Error:** ${err.message}`, steps: newSteps, streaming: false, toolStatus: null }
      })
    } finally {
      setIsLoading(false)
    }
  }, [sessionId, model, isLoading, refreshSessions])

  const isHome = messages.length === 0

  if (!isAuthenticated) {
    return (
      <ThemeContext.Provider value={{ theme, toggleTheme }}>
        <LoginPage onLogin={handleLogin} />
      </ThemeContext.Provider>
    )
  }

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      <div className="app-layout">
        <Sidebar
          onNewChat={handleNewChat}
          onLoadSession={handleLoadSession}
          onDeleteSession={handleDeleteSession}
          sessions={sessions}
          sessionsLoading={sessionsLoading}
          activeSessionId={sessionId}
          isHome={isHome}
          onLogout={handleLogout}
        />
        <main className="main-content">
          {isHome ? (
            <HomePage
              onSubmit={handleSubmit}
              isLoading={isLoading}
            />
          ) : (
            <ResultsPage
              messages={messages}
              isLoading={isLoading}
              onSubmit={handleSubmit}
            />
          )}
        </main>
      </div>
    </ThemeContext.Provider>
  )
}
