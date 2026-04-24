import { useState } from 'react'

const SAMPLE_CODE = `def get_user(id):
    query = f"SELECT * FROM users WHERE id = {id}"
    return db.execute(query)

def process(data):
    result = data.get("key").strip()
    return result

def run_command(user_input):
    os.system("echo " + user_input)
    password = "admin123"
    return True`

const LANGUAGES = ['python', 'javascript', 'typescript', 'java', 'go', 'rust', 'c', 'cpp']

const EXT_MAP = {
  python: 'py', javascript: 'js', typescript: 'ts',
  java: 'java', go: 'go', rust: 'rs', c: 'c', cpp: 'cpp',
}

const TYPE_SHORT = { bug: 'BUG', security: 'SEC', performance: 'PERF', style: 'STY' }

const SEV_COLOR = {
  high:   'var(--red)',
  medium: 'var(--orange)',
  low:    'var(--text-3)',
}

const SEV_DIM = {
  high:   'var(--red-dim)',
  medium: 'var(--orange-dim)',
  low:    'var(--surface)',
}

export default function ReviewPage() {
  const [code, setCode]         = useState('')
  const [language, setLanguage] = useState('python')
  const [findings, setFindings] = useState(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)
  const [time, setTime]         = useState(null)

  const API_BASE   = import.meta.env.VITE_API_URL || ''
  const TIMEOUT_MS = 60000

  async function runReview() {
    if (!code.trim()) return
    setLoading(true)
    setError(null)
    setFindings(null)
    setTime(null)

    const controller = new AbortController()
    const tid = setTimeout(() => controller.abort(), TIMEOUT_MS)

    try {
      const resp = await fetch(`${API_BASE}/api/review-snippet`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          code,
          language,
          filename: `snippet.${EXT_MAP[language] || language}`,
        }),
      })

      if (!resp.ok) {
        let detail = `server error (${resp.status})`
        try { const e = await resp.json(); detail = e.detail || detail } catch (_) {}
        throw new Error(detail)
      }

      const data = await resp.json()
      setFindings(data.findings)
      setTime(data.time_seconds)
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Request timed out — the backend may be cold-starting. Wait 30s and retry.')
      } else if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        setError('Cannot reach backend — it may be starting up. Wait 30s and retry.')
      } else {
        setError(err.message)
      }
    } finally {
      clearTimeout(tid)
      setLoading(false)
    }
  }

  function loadSample() {
    setCode(SAMPLE_CODE)
    setLanguage('python')
    setFindings(null)
    setError(null)
  }

  const lineCount = code ? code.split('\n').length : 0

  return (
    <div style={{ animation: 'fadeUp 0.35s ease-out both' }}>

      {/* ── hero ── */}
      <div style={{ paddingBottom: '36px', borderBottom: '1px solid var(--border)', marginBottom: '32px' }}>
        <div style={{
          fontFamily: 'IBM Plex Mono, monospace',
          fontSize: '10px',
          fontWeight: 500,
          letterSpacing: '0.2em',
          color: 'var(--amber)',
          marginBottom: '12px',
          animation: 'fadeUp 0.3s ease-out both',
        }}>
          CODE SCANNER // v0.2.0
        </div>
        <h1 style={{
          fontFamily: 'Syne, sans-serif',
          fontWeight: 900,
          fontSize: 'clamp(36px, 6vw, 60px)',
          lineHeight: 0.95,
          letterSpacing: '-0.03em',
          color: 'var(--text)',
          marginBottom: '16px',
          animation: 'fadeUp 0.35s ease-out both',
          animationDelay: '0.05s',
        }}>
          SCAN YOUR<br />CODE.
        </h1>
        <p style={{
          fontFamily: 'IBM Plex Sans, sans-serif',
          fontWeight: 300,
          fontSize: '14px',
          lineHeight: 1.7,
          color: 'var(--text-2)',
          maxWidth: '420px',
          animation: 'fadeUp 0.35s ease-out both',
          animationDelay: '0.1s',
        }}>
          Paste any snippet. The ML classifier scores bug risk in 2ms,
          then Claude reviews only the high-risk parts.
        </p>
      </div>

      {/* ── editor ── */}
      <div style={{ marginBottom: '12px', animation: 'fadeUp 0.35s ease-out both', animationDelay: '0.15s' }}>
        <div className="editor-wrap">
          {/* editor top bar */}
          <div className="editor-bar">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {/* terminal dots */}
              <div style={{ display: 'flex', gap: '5px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--border-2)' }} />
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--border-2)' }} />
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--border-2)' }} />
              </div>
              {/* language selector */}
              <select
                value={language}
                onChange={e => setLanguage(e.target.value)}
                style={{
                  background: 'none',
                  border: 'none',
                  outline: 'none',
                  fontFamily: 'IBM Plex Mono, monospace',
                  fontSize: '11px',
                  fontWeight: 500,
                  color: 'var(--text-2)',
                  cursor: 'pointer',
                  letterSpacing: '0.05em',
                }}
              >
                {LANGUAGES.map(l => <option key={l} value={l} style={{ background: '#111' }}>{l}</option>)}
              </select>
              <span style={{
                fontFamily: 'IBM Plex Mono, monospace',
                fontSize: '11px',
                color: 'var(--text-3)',
              }}>
                snippet.{EXT_MAP[language] || language}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              {lineCount > 0 && (
                <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: '10px', color: 'var(--text-3)' }}>
                  {lineCount} {lineCount === 1 ? 'line' : 'lines'}
                </span>
              )}
              <button
                onClick={loadSample}
                style={{
                  background: 'none',
                  border: 'none',
                  fontFamily: 'IBM Plex Mono, monospace',
                  fontSize: '10px',
                  letterSpacing: '0.08em',
                  color: 'var(--text-3)',
                  cursor: 'pointer',
                  transition: 'color 0.15s ease',
                  textTransform: 'uppercase',
                }}
                onMouseEnter={e => e.currentTarget.style.color = 'var(--amber)'}
                onMouseLeave={e => e.currentTarget.style.color = 'var(--text-3)'}
              >
                load sample ↓
              </button>
            </div>
          </div>

          {/* textarea */}
          <textarea
            className="editor-textarea"
            value={code}
            onChange={e => { setCode(e.target.value); setFindings(null) }}
            placeholder="// paste code here..."
            rows={14}
            spellCheck={false}
          />
        </div>
      </div>

      {/* ── scan button ── */}
      <div style={{ marginBottom: '24px', animation: 'fadeUp 0.35s ease-out both', animationDelay: '0.2s' }}>
        <button
          onClick={runReview}
          disabled={!code.trim() || loading}
          className={`btn-scan${loading ? ' loading' : ''}`}
        >
          {loading ? (
            <>
              <span style={{
                width: '12px',
                height: '12px',
                border: '2px solid var(--text-3)',
                borderTopColor: 'var(--amber)',
                borderRadius: '50%',
                animation: 'spin 0.7s linear infinite',
                flexShrink: 0,
              }} />
              SCANNING...
            </>
          ) : (
            <>
              <span style={{ fontSize: '14px' }}>▸</span>
              SCAN CODE
            </>
          )}
        </button>
      </div>

      {/* ── rate limit note ── */}
      <div style={{
        fontFamily: 'IBM Plex Mono, monospace',
        fontSize: '10px',
        letterSpacing: '0.08em',
        color: 'var(--text-3)',
        marginBottom: '24px',
        animation: 'fadeUp 0.35s ease-out both',
        animationDelay: '0.22s',
      }}>
        Rate limited to 10 scans per minute, 50 per day.
      </div>

      {/* ── error ── */}
      {error && (
        <div style={{
          border: '1px solid var(--red)',
          background: 'var(--red-dim)',
          padding: '12px 16px',
          marginBottom: '24px',
          fontFamily: 'IBM Plex Mono, monospace',
          fontSize: '12px',
          color: 'var(--red)',
          animation: 'fadeUp 0.25s ease-out both',
        }}>
          ✗ {error}
        </div>
      )}

      {/* ── results ── */}
      {findings && (
        <div style={{ animation: 'fadeUp 0.3s ease-out both' }}>

          {/* summary bar */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '14px 20px',
            background: findings.length === 0 ? 'var(--green-dim)' : 'var(--red-dim)',
            border: `1px solid ${findings.length === 0 ? 'rgba(34,197,94,0.25)' : 'rgba(255,64,64,0.25)'}`,
            marginBottom: '0',
            borderBottom: findings.length > 0 ? '1px solid var(--border)' : undefined,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
              <span style={{
                fontFamily: 'Syne, sans-serif',
                fontWeight: 800,
                fontSize: '16px',
                letterSpacing: '-0.01em',
                color: findings.length === 0 ? 'var(--green)' : 'var(--red)',
              }}>
                {findings.length === 0 ? '✓ CLEAN' : `${findings.length} ISSUE${findings.length !== 1 ? 'S' : ''} FOUND`}
              </span>
              {findings.length > 0 && (
                <div style={{ display: 'flex', gap: '16px' }}>
                  {['bug', 'security', 'performance', 'style'].map(type => {
                    const count = findings.filter(f => f.type === type).length
                    return count > 0 ? (
                      <span key={type} style={{
                        fontFamily: 'IBM Plex Mono, monospace',
                        fontSize: '10px',
                        color: 'var(--text-2)',
                        letterSpacing: '0.1em',
                      }}>
                        {count} {TYPE_SHORT[type] || type.toUpperCase()}
                      </span>
                    ) : null
                  })}
                </div>
              )}
            </div>
            {time != null && (
              <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: '10px', color: 'var(--text-3)' }}>
                {time}s
              </span>
            )}
          </div>

          {/* findings list */}
          {findings.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '48px 24px',
              border: '1px solid rgba(34,197,94,0.15)',
              borderTop: 'none',
            }}>
              <div style={{
                fontFamily: 'Syne, sans-serif',
                fontWeight: 900,
                fontSize: '48px',
                color: 'var(--green)',
                opacity: 0.15,
                lineHeight: 1,
                marginBottom: '12px',
              }}>✓</div>
              <p style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: '12px', color: 'var(--text-3)', letterSpacing: '0.1em' }}>
                NO ISSUES DETECTED
              </p>
            </div>
          ) : (
            <div style={{ border: '1px solid var(--border)', borderTop: 'none' }}>
              {findings.map((f, i) => {
                const sevColor = SEV_COLOR[f.severity] || SEV_COLOR.low
                const sevDim   = SEV_DIM[f.severity]   || SEV_DIM.low
                return (
                  <div
                    key={i}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'auto auto auto 1fr',
                      gap: '0 20px',
                      alignItems: 'start',
                      padding: '16px 20px',
                      borderBottom: i < findings.length - 1 ? '1px solid var(--border)' : 'none',
                      borderLeft: `3px solid ${sevColor}`,
                      background: 'var(--surface)',
                      transition: 'background 0.1s ease',
                      animation: 'fadeUp 0.3s ease-out both',
                      animationDelay: `${i * 0.06}s`,
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-2)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'var(--surface)'}
                  >
                    {/* type badge */}
                    <span style={{
                      fontFamily: 'IBM Plex Mono, monospace',
                      fontSize: '10px',
                      fontWeight: 500,
                      letterSpacing: '0.1em',
                      color: sevColor,
                      background: sevDim,
                      padding: '3px 7px',
                      border: `1px solid ${sevColor}`,
                      whiteSpace: 'nowrap',
                      lineHeight: 1.4,
                    }}>
                      {TYPE_SHORT[f.type] || f.type.toUpperCase()}
                    </span>

                    {/* severity */}
                    <span style={{
                      fontFamily: 'IBM Plex Mono, monospace',
                      fontSize: '10px',
                      letterSpacing: '0.08em',
                      color: 'var(--text-3)',
                      whiteSpace: 'nowrap',
                      paddingTop: '3px',
                    }}>
                      {f.severity.toUpperCase()}
                    </span>

                    {/* line */}
                    <span style={{
                      fontFamily: 'IBM Plex Mono, monospace',
                      fontSize: '10px',
                      color: 'var(--text-3)',
                      whiteSpace: 'nowrap',
                      paddingTop: '3px',
                    }}>
                      {f.line > 0 ? `L.${f.line}` : '—'}
                    </span>

                    {/* message + code snippet */}
                    <div style={{ minWidth: 0 }}>
                      <p style={{
                        fontFamily: 'IBM Plex Sans, sans-serif',
                        fontWeight: 300,
                        fontSize: '13px',
                        lineHeight: 1.6,
                        color: 'var(--text)',
                        marginBottom: f.line_content ? '10px' : 0,
                      }}>
                        {f.message}
                      </p>
                      {f.line_content && (
                        <div style={{
                          background: '#050505',
                          border: '1px solid var(--border)',
                          borderLeft: `2px solid ${sevColor}`,
                          padding: '8px 12px',
                        }}>
                          <code style={{
                            fontFamily: 'IBM Plex Mono, monospace',
                            fontSize: '11px',
                            color: sevColor,
                            opacity: 0.9,
                          }}>
                            {f.line_content}
                          </code>
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* ── empty state ── */}
      {!findings && !loading && !code.trim() && (
        <div style={{
          textAlign: 'center',
          padding: '64px 24px',
          animation: 'fadeIn 0.5s ease-out both',
          animationDelay: '0.25s',
        }}>
          <div style={{
            fontFamily: 'IBM Plex Mono, monospace',
            fontSize: '48px',
            color: 'var(--border-2)',
            lineHeight: 1,
            marginBottom: '16px',
            letterSpacing: '-0.05em',
          }}>
            { '{ }' }
          </div>
          <p style={{
            fontFamily: 'IBM Plex Mono, monospace',
            fontSize: '11px',
            letterSpacing: '0.12em',
            color: 'var(--text-3)',
            textTransform: 'uppercase',
          }}>
            Paste code or load a sample to begin
          </p>
        </div>
      )}
    </div>
  )
}
