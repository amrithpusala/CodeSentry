import { useState } from 'react'
import ReviewPage from './components/ReviewPage'
import HowItWorksPage from './components/HowItWorksPage'
import AboutPage from './components/AboutPage'

const TABS = [
  { id: 'review',  label: 'Review'       },
  { id: 'how',     label: 'How It Works' },
  { id: 'about',   label: 'About'        },
]

export default function App() {
  const [tab, setTab] = useState('review')

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* ── header ── */}
      <header style={{ borderBottom: '1px solid var(--border)', animation: 'fadeIn 0.3s ease-out both' }}>
        <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '0 24px' }}>
          {/* wordmark row */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '18px', paddingBottom: '14px' }}>
            <button
              onClick={() => setTab('review')}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: 0,
              }}
            >
              {/* mark */}
              <span style={{
                width: '28px',
                height: '28px',
                border: '1px solid var(--amber)',
                background: 'var(--amber-dim)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontFamily: 'IBM Plex Mono, monospace',
                fontSize: '11px',
                fontWeight: 500,
                color: 'var(--amber)',
                flexShrink: 0,
              }}>
                CS
              </span>
              <span style={{
                fontFamily: 'Syne, sans-serif',
                fontWeight: 900,
                fontSize: '17px',
                letterSpacing: '-0.02em',
                color: 'var(--text)',
              }}>
                CODESENTRY
              </span>
            </button>

            <a
              href="https://github.com/amrithpusala/CodeSentry"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                fontFamily: 'IBM Plex Mono, monospace',
                fontSize: '11px',
                color: 'var(--text-3)',
                textDecoration: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                transition: 'color 0.15s ease',
              }}
              onMouseEnter={e => e.currentTarget.style.color = 'var(--text-2)'}
              onMouseLeave={e => e.currentTarget.style.color = 'var(--text-3)'}
            >
              github ↗
            </a>
          </div>

          {/* tab nav */}
          <nav style={{ display: 'flex', gap: 0, marginBottom: '-1px' }}>
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`nav-tab${tab === t.id ? ' active' : ''}`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* ── main content ── */}
      <main
        key={tab}
        style={{
          flex: 1,
          maxWidth: '1000px',
          width: '100%',
          margin: '0 auto',
          padding: '40px 24px 64px',
        }}
      >
        {tab === 'review' && <ReviewPage />}
        {tab === 'how'    && <HowItWorksPage />}
        {tab === 'about'  && <AboutPage />}
      </main>

      {/* ── footer ── */}
      <footer style={{ borderTop: '1px solid var(--border)' }}>
        <div style={{
          maxWidth: '1000px',
          margin: '0 auto',
          padding: '16px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: '10px', color: 'var(--text-3)', letterSpacing: '0.1em' }}>
            PYTORCH + CLAUDE + FASTAPI
          </span>
          <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: '10px', color: 'var(--text-3)', letterSpacing: '0.1em' }}>
            AMRITH PUSALA
          </span>
        </div>
      </footer>
    </div>
  )
}
