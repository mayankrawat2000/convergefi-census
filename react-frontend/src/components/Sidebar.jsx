import { useState } from 'react'
import { useTheme } from '../App'
import logo from '../logo.png'

// ─── Icons ─────────────────────────────────────────────────────────────────────

const PlusIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
       strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
    <line x1="12" y1="5" x2="12" y2="19" />
    <line x1="5"  y1="12" x2="19" y2="12" />
  </svg>
)

const TrashIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
       strokeLinecap="round" strokeLinejoin="round" width="13" height="13">
    <polyline points="3,6 5,6 21,6" />
    <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" />
    <path d="M10 11v6M14 11v6" />
    <path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2" />
  </svg>
)

const SunIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"
       strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
    <circle cx="12" cy="12" r="5" />
    <line x1="12" y1="1"  x2="12" y2="3" />
    <line x1="12" y1="21" x2="12" y2="23" />
    <line x1="4.22"  y1="4.22"  x2="5.64"  y2="5.64" />
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
    <line x1="1"  y1="12" x2="3"  y2="12" />
    <line x1="21" y1="12" x2="23" y2="12" />
    <line x1="4.22"  y1="19.78" x2="5.64"  y2="18.36" />
    <line x1="18.36" y1="5.64"  x2="19.78" y2="4.22" />
  </svg>
)

const MoonIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"
       strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
    <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
  </svg>
)

const ChatIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"
       strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
  </svg>
)

const LogOutIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"
       strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
    <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
    <polyline points="16 17 21 12 16 7" />
    <line x1="21" y1="12" x2="9" y2="12" />
  </svg>
)

// ─── Relative time helper ──────────────────────────────────────────────────────

function relativeTime(isoStr) {
  if (!isoStr) return ''
  const diff = Date.now() - new Date(isoStr).getTime()
  const mins  = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days  = Math.floor(diff / 86400000)
  if (mins < 1)   return 'just now'
  if (mins < 60)  return `${mins}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 7)   return `${days}d ago`
  return new Date(isoStr).toLocaleDateString()
}

// ─── Session Item ──────────────────────────────────────────────────────────────

function SessionItem({ session, isActive, onLoad, onDelete }) {
  const [hovered, setHovered] = useState(false)

  return (
    <div
      className={`session-item ${isActive ? 'active' : ''}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        className="session-item-btn"
        onClick={() => onLoad(session.session_id)}
        title={session.title}
        aria-label={`Load session: ${session.title}`}
      >
        <ChatIcon />
        <div className="session-item-content">
          <span className="session-item-title">{session.title || 'Untitled'}</span>
          <span className="session-item-time">{relativeTime(session.updated_at)}</span>
        </div>
      </button>

      {hovered && (
        <button
          className="session-delete-btn"
          onClick={e => { e.stopPropagation(); onDelete(session.session_id) }}
          title="Delete session"
          aria-label="Delete this session"
        >
          <TrashIcon />
        </button>
      )}
    </div>
  )
}

// ─── Sidebar ───────────────────────────────────────────────────────────────────

export default function Sidebar({ onNewChat, onLoadSession, onDeleteSession, sessions, sessionsLoading, activeSessionId, isHome, onLogout }) {
  const { theme, toggleTheme } = useTheme()

  return (
    <nav className="sidebar" aria-label="Navigation">
      {/* Header */}
      <div className="sidebar-header">
        <div className="sidebar-logo" title="Converge">
          <img src={logo} alt="Converge" className="sidebar-logo-img" />
        </div>
        <button
          id="sidebar-new-chat"
          className="sidebar-new-chat-btn"
          onClick={onNewChat}
          title="New Chat"
          aria-label="New Chat"
        >
          <PlusIcon />
          <span>New Chat</span>
        </button>
      </div>

      {/* Session History */}
      <div className="sidebar-sessions">
        <div className="sidebar-section-label">Recent</div>

        {sessionsLoading ? (
          <div className="sidebar-sessions-loading">
            <div className="sidebar-loading-dots">
              <span /><span /><span />
            </div>
          </div>
        ) : sessions.length === 0 ? (
          <div className="sidebar-empty">No chat history yet</div>
        ) : (
          <div className="sidebar-sessions-list">
            {sessions.map(s => (
              <SessionItem
                key={s.session_id}
                session={s}
                isActive={s.session_id === activeSessionId && !isHome}
                onLoad={onLoadSession}
                onDelete={onDeleteSession}
              />
            ))}
          </div>
        )}
      </div>

      <div className="sidebar-spacer" />

      {/* Theme Toggle & Logout */}
      <div className="sidebar-footer">
        <div className="theme-toggle-wrapper">
          <button
            id="sidebar-theme-toggle"
            className={`theme-toggle-switch ${theme}`}
            onClick={(e) => toggleTheme(e)}
            title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
            aria-label="Toggle theme"
          >
            <div className="theme-toggle-thumb" />
            <div className="theme-toggle-option light">
              <SunIcon />
              <span>Light</span>
            </div>
            <div className="theme-toggle-option dark">
              <MoonIcon />
              <span>Dark</span>
            </div>
          </button>
        </div>
        <div className="sidebar-logout-wrapper">
          <button
            id="sidebar-logout-btn"
            className="sidebar-logout-btn"
            onClick={onLogout}
            title="Log out"
            aria-label="Log out of session"
          >
            <LogOutIcon />
            <span>Log out</span>
          </button>
        </div>
      </div>
    </nav>
  )
}
