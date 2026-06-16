// Thin API client — uses absolute URLs in production to bypass Vercel proxy limits,
// and relative URLs locally for Vite's dev proxy.

const API_BASE = import.meta.env.PROD 
  ? (import.meta.env.VITE_API_URL || 'https://convergefi-census.onrender.com')
  : '';

export async function sendChat(message, sessionId, model) {
  const resp = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, model }),
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`API error ${resp.status}: ${text}`)
  }
  return resp.json()
}

/**
 * Async generator that connects to /api/chat/stream and yields parsed event objects:
 *   { type: 'tool',  name: '...' }
 *   { type: 'chunk', text: '...' }
 *   { type: 'done',  citations, artifacts, logs }
 *   { type: 'error', message: '...' }
 */
export async function* streamChat(message, sessionId, model) {
  const resp = await fetch(`${API_BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, model }),
  })

  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`API error ${resp.status}: ${text}`)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // SSE lines are separated by '\n\n'
    const parts = buffer.split('\n\n')
    buffer = parts.pop() // keep the incomplete last part

    for (const part of parts) {
      for (const line of part.split('\n')) {
        if (line.startsWith('data: ')) {
          const payload = line.slice(6).trim()
          if (payload) {
            try {
              yield JSON.parse(payload)
            } catch (e) {
              console.warn('Failed to parse SSE payload:', payload)
            }
          }
        }
      }
    }
  }
}

// ─── Session Management ────────────────────────────────────────────────────────

/** List all sessions (newest first). Returns [{ session_id, title, updated_at }] */
export async function listSessions() {
  try {
    const resp = await fetch(`${API_BASE}/api/sessions`)
    if (!resp.ok) return []
    return resp.json()
  } catch (_) { return [] }
}

/** Load full message list for a session (for UI replay). */
export async function loadSession(sessionId) {
  try {
    const resp = await fetch(`${API_BASE}/api/sessions/${sessionId}`)
    if (!resp.ok) return null
    return resp.json()
  } catch (_) { return null }
}

/** Delete a session from MongoDB. */
export async function deleteSession(sessionId) {
  try {
    await fetch(`${API_BASE}/api/sessions/${sessionId}`, { method: 'DELETE' })
  } catch (_) { /* best-effort */ }
}

/** Clear history for a session (alias for deleteSession). */
export async function clearHistory(sessionId) {
  return deleteSession(sessionId)
}

export async function getHealth() {
  try {
    const resp = await fetch(`${API_BASE}/api/health`)
    if (!resp.ok) return { status: 'offline' }
    return resp.json()
  } catch (_) {
    return { status: 'offline' }
  }
}

/** Validate credentials against backend env USER_ID/PASSWORD. Returns true on success. */
export async function login(userId, password) {
  try {
    const resp = await fetch(`${API_BASE}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, password }),
    })
    return resp.ok
  } catch (_) {
    return false
  }
}
