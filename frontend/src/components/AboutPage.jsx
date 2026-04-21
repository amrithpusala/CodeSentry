const STACK = [
  { icon: 'API',  name: 'FastAPI',      role: 'API + Webhooks'   },
  { icon: 'ML',   name: 'PyTorch',      role: 'Risk Classifier'  },
  { icon: 'LLM',  name: 'Claude API',   role: 'Code Review'      },
  { icon: 'UI',   name: 'React + Vite', role: 'Dashboard'        },
  { icon: 'GH',   name: 'GitHub API',   role: 'PR Integration'   },
  { icon: 'CSS',  name: 'Tailwind CSS', role: 'Styling'          },
]

const FEATURES = [
  { name: 'Automatic PR Reviews',  desc: 'Triggers on PR open via GitHub webhooks' },
  { name: 'Bug Risk Classifier',   desc: 'PyTorch model trained on 1,200+ real bug-fix commits' },
  { name: 'Smart Triage',          desc: 'Only high-risk chunks sent to LLM — 40–60% API cost reduction' },
  { name: 'Cross-File Context',    desc: 'Reviews check signatures across all changed files and verify interface consistency' },
  { name: 'Fix Suggestions',       desc: 'Each finding includes a concrete code fix and a confidence score; low-confidence findings are filtered' },
  { name: 'Inline Comments',       desc: 'Findings posted on the PR diff, grouped when the same pattern appears in multiple files' },
  { name: 'Multi-Language',        desc: 'Python, JS, TS, Java, Go, Rust, C, and more' },
  { name: 'Snippet Review',        desc: 'Paste any code snippet in this dashboard for instant analysis' },
]

export default function AboutPage() {
  return (
    <div style={{ animation: 'fadeUp 0.35s ease-out both' }}>

      {/* ── hero ── */}
      <div style={{ paddingBottom: '36px', borderBottom: '1px solid var(--border)', marginBottom: '36px' }}>
        <div style={{
          fontFamily: 'IBM Plex Mono, monospace',
          fontSize: '10px',
          fontWeight: 500,
          letterSpacing: '0.2em',
          color: 'var(--amber)',
          marginBottom: '12px',
        }}>
          ABOUT // ML@PURDUE SYMPOSIUM PROJECT
        </div>
        <h1 style={{
          fontFamily: 'Syne, sans-serif',
          fontWeight: 900,
          fontSize: 'clamp(36px, 6vw, 60px)',
          lineHeight: 0.95,
          letterSpacing: '-0.03em',
          color: 'var(--text)',
          marginBottom: '16px',
        }}>
          ABOUT.
        </h1>
        <p style={{
          fontFamily: 'IBM Plex Sans, sans-serif',
          fontWeight: 300,
          fontSize: '14px',
          lineHeight: 1.7,
          color: 'var(--text-2)',
          maxWidth: '460px',
        }}>
          An AI code review bot that combines a custom ML classifier with
          LLM analysis to catch bugs in pull requests.
        </p>
      </div>

      {/* ── problem / solution ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '1px',
        background: 'var(--border)',
        border: '1px solid var(--border)',
        marginBottom: '40px',
        animation: 'fadeUp 0.35s ease-out both',
        animationDelay: '0.08s',
      }}>
        <div style={{ background: 'var(--surface)', padding: '28px' }}>
          <div style={{
            fontFamily: 'IBM Plex Mono, monospace',
            fontSize: '10px',
            fontWeight: 500,
            letterSpacing: '0.15em',
            color: 'var(--red)',
            marginBottom: '14px',
          }}>
            THE PROBLEM
          </div>
          <p style={{
            fontFamily: 'IBM Plex Sans, sans-serif',
            fontWeight: 300,
            fontSize: '13px',
            lineHeight: 1.75,
            color: 'var(--text-2)',
          }}>
            Copilot Code Review costs $10–19/month and is a black-box LLM wrapper. It sends every
            code change to GPT regardless of risk, wasting API calls on trivial changes. There's
            no custom ML, no transparency, and no way to inspect or retrain the model.
          </p>
        </div>

        <div style={{ background: 'var(--surface)', padding: '28px' }}>
          <div style={{
            fontFamily: 'IBM Plex Mono, monospace',
            fontSize: '10px',
            fontWeight: 500,
            letterSpacing: '0.15em',
            color: 'var(--green)',
            marginBottom: '14px',
          }}>
            THE SOLUTION
          </div>
          <p style={{
            fontFamily: 'IBM Plex Sans, sans-serif',
            fontWeight: 300,
            fontSize: '13px',
            lineHeight: 1.75,
            color: 'var(--text-2)',
          }}>
            CodeSentry uses a two-stage pipeline. A custom PyTorch classifier trained on 1,200+
            real bug-fix commits scores each code chunk in 2ms. Only high-risk chunks (above 0.6
            threshold) get sent to Claude — cutting API costs 40–60% while maintaining 73% bug
            recall. Reviews include cross-file context, full file structure, and confidence-filtered
            fix suggestions.
          </p>
        </div>
      </div>

      {/* ── tech stack ── */}
      <div style={{ marginBottom: '40px', animation: 'fadeUp 0.35s ease-out both', animationDelay: '0.12s' }}>
        <div className="section-label">Tech stack</div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
          gap: '1px',
          background: 'var(--border)',
          border: '1px solid var(--border)',
        }}>
          {STACK.map((t, i) => (
            <div
              key={i}
              className="tech-tag"
              style={{
                animation: 'fadeUp 0.3s ease-out both',
                animationDelay: `${0.14 + i * 0.05}s`,
              }}
            >
              <div className="tech-icon">{t.icon}</div>
              <div>
                <div style={{
                  fontFamily: 'IBM Plex Sans, sans-serif',
                  fontWeight: 500,
                  fontSize: '13px',
                  color: 'var(--text)',
                  marginBottom: '2px',
                }}>
                  {t.name}
                </div>
                <div style={{
                  fontFamily: 'IBM Plex Mono, monospace',
                  fontSize: '10px',
                  color: 'var(--text-3)',
                  letterSpacing: '0.05em',
                }}>
                  {t.role}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── features ── */}
      <div style={{ marginBottom: '40px', animation: 'fadeUp 0.35s ease-out both', animationDelay: '0.16s' }}>
        <div className="section-label">Features</div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
          gap: '1px',
          background: 'var(--border)',
          border: '1px solid var(--border)',
        }}>
          {FEATURES.map((f, i) => (
            <div
              key={i}
              className="feature-card"
              style={{
                animation: 'fadeUp 0.3s ease-out both',
                animationDelay: `${0.18 + i * 0.04}s`,
              }}
            >
              <div style={{
                fontFamily: 'IBM Plex Sans, sans-serif',
                fontWeight: 500,
                fontSize: '13px',
                color: 'var(--text)',
                marginBottom: '5px',
              }}>
                {f.name}
              </div>
              <div style={{
                fontFamily: 'IBM Plex Sans, sans-serif',
                fontWeight: 300,
                fontSize: '12px',
                lineHeight: 1.6,
                color: 'var(--text-3)',
              }}>
                {f.desc}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── author ── */}
      <div style={{
        border: '1px solid var(--border)',
        background: 'var(--surface)',
        padding: '36px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '24px',
        flexWrap: 'wrap',
        animation: 'fadeUp 0.35s ease-out both',
        animationDelay: '0.28s',
      }}>
        <div>
          <div style={{
            fontFamily: 'IBM Plex Mono, monospace',
            fontSize: '10px',
            fontWeight: 500,
            letterSpacing: '0.15em',
            color: 'var(--text-3)',
            marginBottom: '8px',
          }}>
            BUILT BY
          </div>
          <h2 style={{
            fontFamily: 'Syne, sans-serif',
            fontWeight: 900,
            fontSize: '24px',
            letterSpacing: '-0.02em',
            color: 'var(--text)',
            lineHeight: 1.1,
            marginBottom: '4px',
          }}>
            Amrith Pusala
          </h2>
          <p style={{
            fontFamily: 'IBM Plex Mono, monospace',
            fontSize: '11px',
            color: 'var(--text-3)',
            letterSpacing: '0.05em',
          }}>
            Computer Science · Purdue University
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <a
            href="https://github.com/amrithpusala/CodeSentry"
            target="_blank"
            rel="noopener noreferrer"
            className="link-btn"
          >
            GitHub ↗
          </a>
          <a
            href="https://linkedin.com/in/amrithpusala"
            target="_blank"
            rel="noopener noreferrer"
            className="link-btn"
          >
            LinkedIn ↗
          </a>
        </div>
      </div>
    </div>
  )
}
