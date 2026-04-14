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

const SEVERITY_STYLES = {
  high: { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400', dot: 'bg-red-400' },
  medium: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400', dot: 'bg-yellow-400' },
  low: { bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-400', dot: 'bg-blue-400' },
}

const TYPE_LABELS = {
  bug: 'BUG', security: 'SECURITY', performance: 'PERF', style: 'STYLE',
}

export default function ReviewPage() {
  const [code, setCode] = useState('')
  const [language, setLanguage] = useState('python')
  const [findings, setFindings] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [time, setTime] = useState(null)

  const API_BASE = import.meta.env.VITE_API_URL || ''

  async function runReview() {
    if (!code.trim()) return
    setLoading(true)
    setError(null)
    setFindings(null)
    setTime(null)

    try {
      const resp = await fetch(`${API_BASE}/api/review-snippet`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: code,
          language: language,
          filename: `snippet.${language === 'python' ? 'py' : language === 'javascript' ? 'js' : language}`,
        }),
      })
      if (!resp.ok) {
        const err = await resp.json()
        throw new Error(err.detail || 'review failed')
      }
      const data = await resp.json()
      setFindings(data.findings)
      setTime(data.time_seconds)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function loadSample() {
    setCode(SAMPLE_CODE)
    setLanguage('python')
    setFindings(null)
    setError(null)
  }

  return (
    <div className="space-y-6" style={{ animation: 'fadeIn .3s ease-out' }}>
      {/* header */}
      <div className="text-center py-4">
        <h2 className="text-2xl font-bold tracking-tight mb-2 font-display">
          Code Review
        </h2>
        <p className="text-zinc-500 text-sm max-w-md mx-auto">
          Paste code below. CodeSentry will scan for bugs, security issues,
          and performance problems using AI analysis.
        </p>
      </div>

      {/* editor */}
      <div className="relative">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <select value={language} onChange={e => setLanguage(e.target.value)}
              className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-1.5
                text-xs font-mono text-zinc-400 focus:outline-none focus:border-zinc-600">
              {LANGUAGES.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
            <button onClick={loadSample}
              className="text-zinc-600 font-mono text-xs hover:text-zinc-400 transition-colors">
              load sample
            </button>
          </div>
          <span className="text-zinc-700 font-mono text-xs">
            {code.split('\n').length} lines
          </span>
        </div>

        <textarea
          value={code}
          onChange={e => { setCode(e.target.value); setFindings(null) }}
          placeholder="// paste your code here..."
          rows={14}
          spellCheck={false}
          className="w-full px-4 py-4 rounded-xl bg-zinc-950 border border-zinc-800
            text-green-300/90 text-sm font-mono leading-relaxed resize-y
            placeholder-zinc-700 focus:outline-none focus:border-green-500/30
            transition-colors"
          style={{ tabSize: 2 }}
        />
      </div>

      {/* scan button */}
      <button onClick={runReview} disabled={!code.trim() || loading}
        className={`w-full py-4 rounded-xl font-semibold text-sm tracking-wider
          uppercase font-display border transition-all duration-300
          ${code.trim() && !loading
            ? 'border-green-500/40 text-green-400 hover:bg-green-500/10 active:scale-[0.99]'
            : 'border-zinc-800 text-zinc-600 cursor-not-allowed'}`}>
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <span className="w-3 h-3 border-2 border-green-500/40 border-t-green-400
              rounded-full animate-spin" />
            Scanning...
          </span>
        ) : (
          <span className="flex items-center justify-center gap-2">
            <span className="font-mono">{'>'}</span> Scan Code
          </span>
        )}
      </button>

      {error && (
        <div className="border border-red-500/20 bg-red-500/5 rounded-xl px-5 py-3
          text-red-400 font-mono text-sm text-center">{error}</div>
      )}

      {/* results */}
      {findings && (
        <div className="space-y-4" style={{ animation: 'slideUp .4s cubic-bezier(.16,1,.3,1)' }}>
          {/* summary bar */}
          <div className="flex items-center justify-between bg-zinc-900/50 border
            border-zinc-800/60 rounded-xl px-5 py-3">
            <div className="flex items-center gap-4">
              <span className={`font-mono text-sm font-bold
                ${findings.length === 0 ? 'text-green-400' : 'text-red-400'}`}>
                {findings.length === 0 ? 'CLEAN' : `${findings.length} ISSUE${findings.length > 1 ? 'S' : ''}`}
              </span>
              {findings.length > 0 && (
                <div className="flex gap-3 text-xs font-mono text-zinc-500">
                  {['bug', 'security', 'performance', 'style'].map(type => {
                    const count = findings.filter(f => f.type === type).length
                    return count > 0 ? <span key={type}>{count} {type}</span> : null
                  })}
                </div>
              )}
            </div>
            {time && (
              <span className="text-zinc-600 font-mono text-xs">{time}s</span>
            )}
          </div>

          {/* findings */}
          {findings.length === 0 ? (
            <div className="text-center py-8">
              <div className="text-3xl mb-2 opacity-30">&#10003;</div>
              <p className="text-zinc-500 font-mono text-sm">no issues found</p>
            </div>
          ) : (
            <div className="space-y-3">
              {findings.map((f, i) => {
                const style = SEVERITY_STYLES[f.severity] || SEVERITY_STYLES.low
                return (
                  <div key={i} className={`${style.bg} border ${style.border} rounded-xl p-4`}
                    style={{ animation: `slideUp ${0.3 + i * 0.1}s cubic-bezier(.16,1,.3,1)` }}>
                    <div className="flex items-start gap-3">
                      <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${style.dot}`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className={`font-mono text-xs font-bold ${style.text}`}>
                            {TYPE_LABELS[f.type] || f.type.toUpperCase()}
                          </span>
                          <span className="text-zinc-600 font-mono text-xs">
                            {f.severity.toUpperCase()}
                          </span>
                          {f.line > 0 && (
                            <span className="text-zinc-700 font-mono text-xs">
                              line {f.line}
                            </span>
                          )}
                        </div>
                        <p className="text-zinc-300 text-sm leading-relaxed">{f.message}</p>
                        {f.line_content && (
                          <div className="mt-2 px-3 py-2 rounded-lg bg-black/30 border border-zinc-800/50">
                            <code className="text-xs font-mono text-red-300/80">{f.line_content}</code>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* empty state */}
      {!findings && !loading && !code.trim() && (
        <div className="text-center py-12" style={{ animation: 'fadeIn .5s ease-out' }}>
          <div className="font-mono text-3xl mb-3 opacity-15">{'{ }'}</div>
          <p className="text-zinc-600 font-mono text-sm">paste code or load a sample to get started</p>
        </div>
      )}
    </div>
  )
}
