import { useEffect, useRef, useCallback } from 'react'

// ─── Icons ────────────────────────────────────────────────────────────────────



const ArrowUpIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
       strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="19" x2="12" y2="5" />
    <polyline points="5,12 12,5 19,12" />
  </svg>
)

const SpinnerIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
       strokeLinecap="round" strokeLinejoin="round" className="spin">
    <path d="M12 3a9 9 0 110 18A9 9 0 0112 3z" strokeOpacity="0.25" />
    <path d="M12 3a9 9 0 019 9" />
  </svg>
)

// ─── Component ────────────────────────────────────────────────────────────────

export default function SearchBox({
  onSubmit,
  isLoading,
  placeholder = 'Ask anything…',
  value,
  setValue,
}) {
  const textareaRef = useRef(null)

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim()
    if (!trimmed || isLoading) return
    onSubmit(trimmed)
    setValue('')
  }, [value, isLoading, onSubmit, setValue])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleInput = (e) => {
    setValue(e.target.value)
  }

  useEffect(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 200) + 'px'
      if (value) {
        el.focus()
      }
    }
  }, [value])

  return (
    <div className="search-card">
      <textarea
        ref={textareaRef}
        id="search-input"
        className="search-textarea"
        placeholder={placeholder}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        rows={1}
        disabled={isLoading}
        aria-label="Search input"
      />

      <div className="search-card-footer">
        {/* Left: empty spacer to push submit to the right */}
        <div className="search-actions-left" />

        {/* Right: submit */}
        <div className="search-actions-right">
          <button
            id="submit-btn"
            className="submit-btn"
            onClick={handleSubmit}
            disabled={!value.trim() || isLoading}
            title="Submit"
            aria-label="Submit query"
          >
            {isLoading ? <SpinnerIcon /> : <ArrowUpIcon />}
          </button>
        </div>
      </div>
    </div>
  )
}
