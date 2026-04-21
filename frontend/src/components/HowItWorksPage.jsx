const STEPS = [
  {
    n: '01',
    title: 'DIFF PARSING',
    sub: 'Webhook → Chunks',
    desc: 'When a PR is opened, CodeSentry receives a GitHub webhook, fetches the unified diff, and breaks it into reviewable code chunks. Non-code files (configs, lockfiles, markdown) are filtered out. Small adjacent changes are merged into logical units.',
  },
  {
    n: '02',
    title: 'FEATURE EXTRACTION',
    sub: '32 signals per chunk',
    desc: 'Each chunk is analyzed for 27 syntax features (size, complexity, risky patterns, code hygiene) plus 5 semantic features: cross-function call depth, import complexity, error-handling ratio, test coverage presence, and commit history risk. Semantic signals adjust the classifier score post-hoc without retraining.',
  },
  {
    n: '03',
    title: 'RISK CLASSIFICATION',
    sub: 'PyTorch · 2ms · threshold 0.6',
    desc: 'A PyTorch feedforward network (3 layers, 128 units) trained on 1,200+ real commits scores each chunk 0→1. Semantic signals apply post-hoc adjustments (e.g. +0.10 for files with >50% bug-fix commit history). Chunks above 0.6 are flagged for deep review.',
  },
  {
    n: '04',
    title: 'CONTEXT BUILDING',
    sub: 'PR meta + file structure + cross-file signatures',
    desc: 'Before sending to the LLM, CodeSentry fetches the PR title and description, extracts function signatures from the full file (not just the diff), and builds a cross-file summary of all other changed files in the PR. Risk classifier flags become a "focus areas" section in the prompt.',
  },
  {
    n: '05',
    title: 'LLM REVIEW',
    sub: 'Claude · high-risk chunks only',
    desc: 'High-risk chunks are sent to Claude with the full context package: PR intent, file structure, cross-file signatures, and risk focus areas. Claude checks for interface mismatches across files. Each finding includes a concrete fix and a confidence score. Findings below 50% confidence are filtered out.',
  },
  {
    n: '06',
    title: 'PR COMMENTS',
    sub: 'Inline · grouped · with suggestions',
    desc: 'Findings are grouped by pattern (the same issue in 3 files becomes one comment noting all locations), formatted with severity indicators, concrete fix suggestions, and confidence scores, then posted as inline PR review comments with a full summary.',
  },
]

const STATS = [
  { label: 'ACCURACY',  value: '63.5%' },
  { label: 'PRECISION', value: '61.8%' },
  { label: 'RECALL',    value: '73.4%' },
  { label: 'F1 SCORE',  value: '0.67'  },
]

const PIPELINE = ['PR OPEN', 'DIFF PARSE', 'RISK SCORE', 'CTX BUILD', 'LLM REVIEW', 'PR COMMENT']

export default function HowItWorksPage() {
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
          ARCHITECTURE // TWO-STAGE PIPELINE
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
          HOW IT<br />WORKS.
        </h1>
        <p style={{
          fontFamily: 'IBM Plex Sans, sans-serif',
          fontWeight: 300,
          fontSize: '14px',
          lineHeight: 1.7,
          color: 'var(--text-2)',
          maxWidth: '460px',
        }}>
          A custom PyTorch classifier triages every code chunk. Only
          high-risk code reaches the LLM — cutting API costs by 40–60%
          while keeping 73% bug recall.
        </p>
      </div>

      {/* ── classifier metrics strip ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        border: '1px solid var(--border)',
        marginBottom: '40px',
        animation: 'fadeUp 0.35s ease-out both',
        animationDelay: '0.08s',
      }}>
        {STATS.map((s, i) => (
          <div key={i} className="stat-block">
            <div style={{
              fontFamily: 'Syne, sans-serif',
              fontWeight: 900,
              fontSize: '28px',
              letterSpacing: '-0.03em',
              color: 'var(--amber)',
              lineHeight: 1,
              marginBottom: '6px',
            }}>
              {s.value}
            </div>
            <div style={{
              fontFamily: 'IBM Plex Mono, monospace',
              fontSize: '9px',
              fontWeight: 500,
              letterSpacing: '0.15em',
              color: 'var(--text-3)',
            }}>
              {s.label}
            </div>
          </div>
        ))}
      </div>
      <p style={{
        fontFamily: 'IBM Plex Mono, monospace',
        fontSize: '10px',
        color: 'var(--text-3)',
        letterSpacing: '0.05em',
        marginBottom: '40px',
        marginTop: '-28px',
      }}>
        Trained on 1,253 samples from 15 open-source repos. High recall prioritized to minimize missed bugs.
      </p>

      {/* ── pipeline flow ── */}
      <div style={{ marginBottom: '40px', animation: 'fadeUp 0.35s ease-out both', animationDelay: '0.12s' }}>
        <div className="section-label">Pipeline</div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 0,
          overflowX: 'auto',
          paddingBottom: '8px',
        }}>
          {PIPELINE.map((label, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
              <div className="pipe-node">
                <div className="pipe-num">{String(i + 1).padStart(2, '0')}</div>
                <span style={{
                  fontFamily: 'IBM Plex Mono, monospace',
                  fontSize: '9px',
                  fontWeight: 500,
                  letterSpacing: '0.1em',
                  color: 'var(--text-3)',
                  textAlign: 'center',
                  whiteSpace: 'nowrap',
                }}>
                  {label}
                </span>
              </div>
              {i < PIPELINE.length - 1 && (
                <div style={{
                  width: '32px',
                  height: '1px',
                  background: 'var(--border-2)',
                  flexShrink: 0,
                  marginBottom: '20px',
                  position: 'relative',
                }}>
                  <span style={{
                    position: 'absolute',
                    right: '-4px',
                    top: '-4px',
                    color: 'var(--border-2)',
                    fontSize: '9px',
                  }}>▸</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ── steps ── */}
      <div style={{ animation: 'fadeUp 0.35s ease-out both', animationDelay: '0.16s' }}>
        <div className="section-label">Step by step</div>
        <div style={{ border: '1px solid var(--border)' }}>
          {STEPS.map((step, i) => (
            <div
              key={i}
              style={{
                display: 'grid',
                gridTemplateColumns: '56px 1fr',
                gap: 0,
                borderBottom: i < STEPS.length - 1 ? '1px solid var(--border)' : 'none',
                animation: 'fadeUp 0.3s ease-out both',
                animationDelay: `${0.18 + i * 0.07}s`,
              }}
            >
              {/* number column */}
              <div style={{
                borderRight: '1px solid var(--border)',
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'center',
                paddingTop: '20px',
                paddingBottom: '20px',
                background: 'var(--surface)',
              }}>
                <span style={{
                  fontFamily: 'Syne, sans-serif',
                  fontWeight: 900,
                  fontSize: '18px',
                  color: 'var(--text-3)',
                  letterSpacing: '-0.02em',
                }}>
                  {step.n}
                </span>
              </div>

              {/* content column */}
              <div
                style={{ padding: '20px 24px', background: 'var(--surface)', transition: 'background 0.1s ease' }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-2)'}
                onMouseLeave={e => e.currentTarget.style.background = 'var(--surface)'}
              >
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginBottom: '10px', flexWrap: 'wrap' }}>
                  <h3 style={{
                    fontFamily: 'Syne, sans-serif',
                    fontWeight: 800,
                    fontSize: '14px',
                    letterSpacing: '0.02em',
                    color: 'var(--text)',
                  }}>
                    {step.title}
                  </h3>
                  <span style={{
                    fontFamily: 'IBM Plex Mono, monospace',
                    fontSize: '10px',
                    color: 'var(--amber)',
                    letterSpacing: '0.05em',
                  }}>
                    {step.sub}
                  </span>
                </div>
                <p style={{
                  fontFamily: 'IBM Plex Sans, sans-serif',
                  fontWeight: 300,
                  fontSize: '13px',
                  lineHeight: 1.7,
                  color: 'var(--text-2)',
                }}>
                  {step.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
