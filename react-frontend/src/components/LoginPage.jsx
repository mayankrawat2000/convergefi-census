import { useState, useCallback, useRef } from 'react'
import { login } from '../api/client'
import logoSrc from '../logo.png'

const EyeIcon = ({ open }) =>
  open ? (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  )

const SpinnerIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
       strokeLinecap="round" strokeLinejoin="round" className="login-spinner">
    <path d="M12 3a9 9 0 110 18A9 9 0 0112 3z" strokeOpacity="0.25" />
    <path d="M12 3a9 9 0 019 9" />
  </svg>
)

export default function LoginPage({ onLogin }) {
  const [userId, setUserId]       = useState('')
  const [password, setPassword]   = useState('')
  const [showPass, setShowPass]   = useState(false)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')
  const [shake, setShake]         = useState(false)
  const cardRef = useRef(null)

  const triggerShake = useCallback(() => {
    setShake(true)
    setTimeout(() => setShake(false), 600)
  }, [])

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault()
    if (!userId.trim() || !password) return
    setLoading(true)
    setError('')

    const ok = await login(userId.trim(), password)
    setLoading(false)

    if (ok) {
      onLogin()
    } else {
      setError('Invalid User ID or Password.')
      triggerShake()
    }
  }, [userId, password, onLogin, triggerShake])

  return (
    <div className="login-page">
      {/* Subtle radial gradient backdrop */}
      <div className="login-bg-gradient" aria-hidden="true" />

      <div className={`login-card${shake ? ' shake' : ''}`} ref={cardRef}>
        {/* Logo */}
        <div className="login-logo-wrap">
          <img src={logoSrc} alt="Converge FI" className="login-logo-img" />
        </div>

        <h1 className="login-heading">Sign in</h1>

        <form onSubmit={handleSubmit} className="login-form" noValidate>
          {/* User ID */}
          <div className="login-field">
            <label htmlFor="login-user-id" className="login-label">User ID</label>
            <input
              id="login-user-id"
              type="text"
              className={`login-input${error ? ' login-input-error' : ''}`}
              placeholder="Enter your user ID"
              value={userId}
              onChange={e => { setUserId(e.target.value); setError('') }}
              autoComplete="username"
              autoFocus
              disabled={loading}
              required
            />
          </div>

          {/* Password */}
          <div className="login-field">
            <label htmlFor="login-password" className="login-label">Password</label>
            <div className="login-password-wrap">
              <input
                id="login-password"
                type={showPass ? 'text' : 'password'}
                className={`login-input login-input-password${error ? ' login-input-error' : ''}`}
                placeholder="Enter your password"
                value={password}
                onChange={e => { setPassword(e.target.value); setError('') }}
                autoComplete="current-password"
                disabled={loading}
                required
              />
              <button
                type="button"
                id="toggle-password-visibility"
                className="login-eye-btn"
                onClick={() => setShowPass(v => !v)}
                tabIndex={-1}
                aria-label={showPass ? 'Hide password' : 'Show password'}
              >
                <EyeIcon open={showPass} />
              </button>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="login-error" role="alert">
              <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14" style={{flexShrink:0}}>
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            id="login-submit-btn"
            type="submit"
            className="login-submit-btn"
            disabled={loading || !userId.trim() || !password}
          >
            {loading ? (
              <>
                <SpinnerIcon />
                <span>Signing in…</span>
              </>
            ) : (
              'Sign in'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
