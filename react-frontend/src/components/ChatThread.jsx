import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import SourceCards from './SourceCards'

// ─── Streaming cursor ─────────────────────────────────────────────────────────
const cursorStyle = {
  display: 'inline-block',
  width: '2px',
  height: '1em',
  background: 'var(--accent)',
  marginLeft: '2px',
  verticalAlign: 'text-bottom',
  borderRadius: '1px',
  animation: 'cursorBlink 0.85s steps(1) infinite',
}

// Inject cursor keyframes once
if (!document.getElementById('cursor-keyframes')) {
  const s = document.createElement('style')
  s.id = 'cursor-keyframes'
  s.textContent = '@keyframes cursorBlink { 0%,100% { opacity:1 } 50% { opacity:0 } }'
  document.head.appendChild(s)
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Replace [N] citation markers with HTML superscript anchors.
 * Deduplicates citations and maps original indices to unique ones.
 */
function injectCitationSuperscripts(text, citations) {
  if (!citations || citations.length === 0) return text

  // Build dedup map: original 1-based index → unique 1-based index
  const seenKeys = new Map()
  const uniqueCites = []
  const origToUnique = {}

  citations.forEach((c, i) => {
    const key = `${c.source_document}::${c.page_number}`
    if (!seenKeys.has(key)) {
      seenKeys.set(key, uniqueCites.length)
      uniqueCites.push(c)
    }
    origToUnique[i + 1] = seenKeys.get(key) + 1
  })

  return text.replace(/\[(\d+)\]/g, (match, num) => {
    const mapped = origToUnique[parseInt(num, 10)]
    return mapped
      ? `<sup><a href="#cite-${mapped}">${mapped}</a></sup>`
      : match
  })
}

// ─── Icons ────────────────────────────────────────────────────────────────────

const SourcesIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"
       strokeLinecap="round" strokeLinejoin="round">
    <path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z" />
    <polyline points="14,2 14,8 20,8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
  </svg>
)

const AnswerIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"
       strokeLinecap="round" strokeLinejoin="round">
    <line x1="8"  y1="6"  x2="21" y2="6" />
    <line x1="8"  y1="12" x2="21" y2="12" />
    <line x1="8"  y1="18" x2="21" y2="18" />
    <circle cx="3" cy="6"  r="0.5" fill="currentColor" />
    <circle cx="3" cy="12" r="0.5" fill="currentColor" />
    <circle cx="3" cy="18" r="0.5" fill="currentColor" />
  </svg>
)

const ArtifactIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"
       strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <circle cx="8.5" cy="8.5" r="1.5" />
    <polyline points="21,15 16,10 5,21" />
  </svg>
)

const ChevronIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
       strokeLinecap="round" strokeLinejoin="round">
    <polyline points="9,18 15,12 9,6" />
  </svg>
)

// ─── Sub-components ───────────────────────────────────────────────────────────

function CitationsExpander({ citations }) {
  const [open, setOpen] = useState(false)
  if (!citations || citations.length === 0) return null

  return (
    <div className="citations-expander">
      <button
        id="citations-toggle"
        className={`citations-toggle ${open ? 'open' : ''}`}
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
      >
        <ChevronIcon />
        {citations.length} source{citations.length !== 1 ? 's' : ''}
      </button>

      {open && (
        <div className="citations-list fade-in">
          {citations.map((cite, idx) => (
            <div key={idx} id={`cite-${idx + 1}`} className="citation-item">
              <strong>[{idx + 1}] {cite.source_document} — p.{cite.page_number}</strong>
              &ldquo;{cite.snippet}&rdquo;
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ArtifactBlock({ artifact }) {
  const { name, type, description } = artifact

  if (type === 'image') {
    return (
      <div style={{ marginTop: 12 }}>
        <img
          src={`/api/artifacts/${name}`}
          alt={description}
          className="artifact-img"
          loading="lazy"
        />
        <p className="artifact-img-caption">{description}</p>
      </div>
    )
  }

  if (type === 'table' || /\.(md|txt|csv)$/i.test(name)) {
    return <ArtifactMarkdown name={name} description={description} />
  }

  return (
    <a
      href={`/api/artifacts/${name}`}
      target="_blank"
      rel="noopener noreferrer"
      className="artifact-link"
    >
      📄 {name} — {description}
    </a>
  )
}

function ArtifactMarkdown({ name, description }) {
  const [content, setContent] = useState(null)

  useEffect(() => {
    fetch(`/api/artifacts/${name}`)
      .then(r => r.ok ? r.text() : Promise.reject())
      .then(setContent)
      .catch(() => setContent('*Could not load artifact.*'))
  }, [name])

  return (
    <div className="artifact-table-wrapper">
      <p className="artifact-img-caption" style={{ marginBottom: 10 }}>{description}</p>
      {content
        ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        : <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Loading…</span>
      }
    </div>
  )
}

function StepsChain({ steps, streaming }) {
  const [open, setOpen] = useState(false)
  if (!steps || steps.length === 0) return null

  const activeStep = steps.find(s => s.status === 'running') || steps[steps.length - 1]

  return (
    <div className="steps-container" style={{ margin: '8px 0 16px 0' }}>
      <button
        id="steps-toggle"
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          background: 'none',
          border: 'none',
          padding: '4px 0',
          fontSize: '0.82rem',
          color: 'var(--text-secondary)',
          fontWeight: 500,
          cursor: 'pointer',
          outline: 'none',
          fontFamily: 'var(--font-sans)',
        }}
        aria-expanded={open}
      >
        <span
          style={{
            transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
            transition: 'transform 0.15s ease',
            display: 'inline-block',
            fontSize: '0.62rem',
            marginRight: 2,
            color: 'var(--text-muted)'
          }}
        >
          ▶
        </span>
        {streaming && activeStep.status === 'running' ? (
          <span style={{ animation: 'spin 1.1s linear infinite', display: 'inline-block' }}>⟳</span>
        ) : (
          <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>✓</span>
        )}
        <span style={{ marginLeft: 4 }}>
          {streaming && activeStep.status === 'running'
            ? `${activeStep.label}…`
            : `Found results through ${steps.length} search step${steps.length !== 1 ? 's' : ''}`}
        </span>
      </button>

      {open && (
        <div
          className="fade-in"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
            paddingLeft: 14,
            marginLeft: 4,
            marginTop: 6,
            borderLeft: '1px solid var(--border)',
            fontSize: '0.78rem',
            color: 'var(--text-muted)',
          }}
        >
          {steps.map((step, idx) => (
            <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {step.status === 'running' ? (
                <span style={{ animation: 'spin 1.1s linear infinite', display: 'inline-block', fontSize: '0.75rem' }}>⟳</span>
              ) : (
                <span style={{ color: 'var(--accent)', fontSize: '0.75rem', fontWeight: 'bold' }}>✓</span>
              )}
              <span>{step.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ChatThread({ messages, isLoading }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Group into (user, assistant?) pairs for rendering
  const pairs = []
  let i = 0
  while (i < messages.length) {
    if (messages[i].role === 'user') {
      const user = messages[i]
      const assistant = messages[i + 1]?.role === 'assistant' ? messages[i + 1] : null
      pairs.push({ user, assistant })
      i += assistant ? 2 : 1
    } else {
      i++
    }
  }

  // Legacy: true when a user message has no assistant yet (old non-streaming path)
  const isLastPending = pairs.length > 0 && !pairs[pairs.length - 1].assistant && isLoading

  return (
    <>
      {pairs.map((pair, pairIdx) => {
        const isLast = pairIdx === pairs.length - 1
        const pending = isLast && isLastPending

        return (
          <div key={pairIdx} className="thread-item fade-in">
            {/* Question heading */}
            <h2 className="thread-question">{pair.user.question}</h2>

            {pending && (
              <div className="thinking-dots" aria-label="Thinking…">
                <span /><span /><span />
              </div>
            )}

            {/* Streaming states */}
            {pair.assistant?.streaming && !pair.assistant.answer && !pair.assistant.toolStatus && (
              <div className="thinking-dots" aria-label="Thinking…">
                <span /><span /><span />
              </div>
            )}
            {pair.assistant?.steps?.length > 0 ? (
              <StepsChain steps={pair.assistant.steps} streaming={pair.assistant.streaming} />
            ) : pair.assistant?.toolStatus ? (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '10px 0',
                fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 450,
              }}>
                <span style={{ animation: 'spin 1.1s linear infinite', display: 'inline-block' }}>⟳</span>
                {pair.assistant.toolStatus}…
              </div>
            ) : null}

            {pair.assistant && (
              <>
                {/* Sources */}
                {pair.assistant.citations?.length > 0 && (
                  <>
                    <div className="section-label">
                      <SourcesIcon />
                      Sources
                    </div>
                    <SourceCards citations={pair.assistant.citations} />
                  </>
                )}

                {/* Answer */}
                {(pair.assistant.answer || !pair.assistant.streaming) && (
                <div className="section-label">
                  <AnswerIcon />
                  Answer
                </div>
                )}
                <div className="answer-body">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeRaw]}
                    components={{
                      // Intercept <img> tags to fix bare artifact filenames from LLM output
                      img: ({ src, alt, ...props }) => {
                        let fixedSrc = src || ''
                        // Bare filename (e.g. "mp_growth_rates.png") or artifacts-relative path
                        if (
                          fixedSrc &&
                          !fixedSrc.startsWith('http') &&
                          !fixedSrc.startsWith('/api/')
                        ) {
                          // Strip any leading "artifacts/" prefix the agent might add
                          const filename = fixedSrc.replace(/^artifacts\//, '').replace(/^\//, '')
                          fixedSrc = `/api/artifacts/${filename}`
                        }
                        return (
                          <img
                            src={fixedSrc}
                            alt={alt}
                            className="artifact-img"
                            style={{ marginTop: 12 }}
                            {...props}
                          />
                        )
                      }
                    }}
                  >
                    {injectCitationSuperscripts(pair.assistant.answer, pair.assistant.citations)}
                  </ReactMarkdown>
                  {/* Blinking cursor while still streaming and answer has text */}
                  {pair.assistant.streaming && pair.assistant.answer && (
                    <span style={cursorStyle} aria-hidden="true" />
                  )}
                </div>

                {/* Artifacts */}
                {pair.assistant.artifacts?.length > 0 && (
                  <>
                    <div className="section-label" style={{ marginTop: 18 }}>
                      <ArtifactIcon />
                      Generated
                    </div>
                    {pair.assistant.artifacts.map((art, artIdx) => (
                      <ArtifactBlock key={artIdx} artifact={art} />
                    ))}
                  </>
                )}
              </>
            )}
          </div>
        )
      })}

      <div ref={bottomRef} />
    </>
  )
}
