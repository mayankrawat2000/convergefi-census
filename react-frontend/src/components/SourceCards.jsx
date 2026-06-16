import { useState, useEffect, useCallback } from 'react'

// ─── PDF Preview Modal ─────────────────────────────────────────────────────────

const API_BASE = import.meta.env.PROD 
  ? (import.meta.env.VITE_API_URL || 'https://convergefi-census.onrender.com')
  : '';

function PdfModal({ cite, onClose }) {
  // Always use the .pdf file — the agent may cite .md filenames
  const rawFilename = cite.source_document.replace(/^.*[\\/]/, '')
  const pdfFilename = rawFilename.replace(/\.md$/i, '.pdf')
  const pdfUrl = `${API_BASE}/api/pdf/${encodeURIComponent(pdfFilename)}#page=${cite.page_number}`

  const shortName = rawFilename
    .replace('PC11_PCA_Data_Highlights_', '')
    .replace(/_/g, ' ')
    .replace(/\.(pdf|md)$/i, '')
    .replace(/PCA Data Highlights /i, '')

  // Close on Escape key
  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose])

  // Prevent body scroll while modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  return (
    <div
      className="pdf-modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`PDF preview: ${shortName}`}
    >
      <div
        className="pdf-modal-container"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="pdf-modal-header">
          <div className="pdf-modal-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"
                 strokeLinecap="round" strokeLinejoin="round" className="pdf-modal-icon">
              <path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z" />
              <polyline points="14,2 14,8 20,8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
            </svg>
            <span>{shortName}</span>
            <span className="pdf-modal-page-badge">Page {cite.page_number}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <a
              href={pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="pdf-modal-open-btn"
              title="Open PDF in new tab"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                   strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
                <polyline points="15,3 21,3 21,9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </svg>
              Open in tab
            </a>
            <button
              className="pdf-modal-close"
              onClick={onClose}
              aria-label="Close PDF preview"
              title="Close (Esc)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                   strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>



        {/* PDF iframe — loads at the right page */}
        <div className="pdf-modal-viewer">
          <div className="pdf-modal-loading">
            <div className="pdf-modal-loading-spinner" />
            <span>Loading PDF… (this may take a moment for large files)</span>
          </div>
          <iframe
            src={pdfUrl}
            title={`${shortName} — page ${cite.page_number}`}
            className="pdf-modal-iframe"
            aria-label="PDF document viewer"
            onLoad={e => {
              // Hide the loading overlay once loaded
              const overlay = e.target.previousSibling
              if (overlay) overlay.style.display = 'none'
              e.target.style.opacity = '1'
            }}
            onError={e => {
              const overlay = e.target.previousSibling
              if (overlay) {
                overlay.innerHTML = `
                  <div style="text-align:center; padding: 24px">
                    <p style="color: var(--text-muted); margin-bottom:16px">
                      Could not load PDF inline. Open it directly:
                    </p>
                    <a href="${pdfUrl}" target="_blank" rel="noopener noreferrer"
                       style="color: var(--accent); font-weight:600; text-decoration: none">
                      Open PDF in new tab →
                    </a>
                  </div>`
              }
            }}
          />
        </div>
      </div>
    </div>
  )
}

// ─── Source Cards ──────────────────────────────────────────────────────────────

export default function SourceCards({ citations }) {
  const [activeCite, setActiveCite] = useState(null)

  if (!citations || citations.length === 0) return null

  // Deduplicate by document+page
  const seen = new Set()
  const unique = []
  for (const cite of citations) {
    const key = `${cite.source_document}::${cite.page_number}`
    if (!seen.has(key)) {
      seen.add(key)
      unique.push(cite)
    }
  }

  const handleClose = useCallback(() => setActiveCite(null), [])

  return (
    <>
      <div className="sources-scroll" role="list" aria-label="Sources">
        {unique.map((cite, idx) => {
          const shortName = cite.source_document
            .replace('PC11_PCA_Data_Highlights_', '')
            .replace(/_/g, ' ')
            .replace(/\.(md|pdf|txt)$/i, '')
            .replace(/PCA Data Highlights /i, '')

          return (
            <button
              key={idx}
              className="source-card source-card-clickable"
              role="listitem"
              id={`source-card-${idx}`}
              title={`Preview: ${shortName} — page ${cite.page_number}`}
              onClick={() => setActiveCite(cite)}
              aria-label={`Open source: ${shortName}, page ${cite.page_number}`}
            >
              <div className="source-card-title">{shortName}</div>
              <div className="source-card-footer">
                <span className="source-card-page">p.&nbsp;{cite.page_number}</span>
                <span className="source-card-num" aria-label={`Source ${idx + 1}`}>
                  {idx + 1}
                </span>
              </div>
              {/* PDF open hint */}
              <div className="source-card-hint">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                     strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
                  <polyline points="15,3 21,3 21,9" />
                  <line x1="10" y1="14" x2="21" y2="3" />
                </svg>
                Preview PDF
              </div>
            </button>
          )
        })}
      </div>

      {activeCite && (
        <PdfModal cite={activeCite} onClose={handleClose} />
      )}
    </>
  )
}
