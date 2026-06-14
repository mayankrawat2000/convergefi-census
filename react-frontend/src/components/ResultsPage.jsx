import { useRef } from 'react'
import ChatThread from './ChatThread'

const ArrowUpIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
       strokeLinecap="round" strokeLinejoin="round" style={{ width: 15, height: 15 }}>
    <line x1="12" y1="19" x2="12" y2="5" />
    <polyline points="5,12 12,5 19,12" />
  </svg>
)

const SpinnerIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
       strokeLinecap="round" strokeLinejoin="round" className="spin"
       style={{ width: 15, height: 15 }}>
    <path d="M12 3a9 9 0 110 18A9 9 0 0112 3z" strokeOpacity="0.25" />
    <path d="M12 3a9 9 0 019 9" />
  </svg>
)

export default function ResultsPage({ messages, isLoading, onSubmit }) {
  const inputRef = useRef(null)

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && inputRef.current?.value.trim() && !isLoading) {
      e.preventDefault()
      const val = inputRef.current.value.trim()
      inputRef.current.value = ''
      onSubmit(val)
    }
  }

  const handleClick = () => {
    const val = inputRef.current?.value.trim()
    if (val && !isLoading) {
      inputRef.current.value = ''
      onSubmit(val)
    }
  }

  return (
    <div className="thread-page">
      {/* Scrollable conversation */}
      <div className="thread-scroll">
        <div className="thread-inner">
          <ChatThread messages={messages} isLoading={isLoading} />
        </div>
      </div>

      {/* Sticky follow-up bar */}
      <div className="followup-bar">
        <div className="followup-card">
          <input
            ref={inputRef}
            id="followup-input"
            className="followup-input"
            placeholder="Ask a follow-up…"
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            aria-label="Follow-up question"
          />

          <button
            id="followup-submit-btn"
            className="submit-btn"
            onClick={handleClick}
            disabled={isLoading}
            title="Submit follow-up"
            aria-label="Submit follow-up"
          >
            {isLoading ? <SpinnerIcon /> : <ArrowUpIcon />}
          </button>
        </div>
      </div>
    </div>
  )
}
