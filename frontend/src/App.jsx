import { useState } from 'react'
import ReviewPage from './components/ReviewPage'
import HowItWorksPage from './components/HowItWorksPage'
import AboutPage from './components/AboutPage'

const TABS = [
  { id: 'review', label: 'Review', icon: '>' },
  { id: 'how', label: 'How It Works', icon: '?' },
  { id: 'about', label: 'About', icon: '#' },
]

export default function App() {
  const [tab, setTab] = useState('review')

  return (
    <div className="relative min-h-screen bg-[#0a0a0a] text-white font-body">
      {/* subtle grid background */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage: 'linear-gradient(rgba(34,197,94,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(34,197,94,0.3) 1px, transparent 1px)',
          backgroundSize: '60px 60px',
        }} />

      <div className="relative z-10">
        {/* header */}
        <header className="border-b border-zinc-800/80">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 pt-5 pb-0">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-green-500/10 border border-green-500/30
                  flex items-center justify-center font-mono text-green-400 text-sm font-bold">
                  {'{}'}
                </div>
                <h1 className="text-xl font-bold tracking-tight cursor-pointer font-display"
                  onClick={() => setTab('review')}>
                  CodeSentry
                </h1>
              </div>
              <a href="https://github.com/amrithpusala/CodeSentry"
                target="_blank" rel="noopener noreferrer"
                className="text-zinc-500 font-mono text-xs hover:text-zinc-300 transition-colors">
                github
              </a>
            </div>

            <div className="flex gap-0 -mb-px">
              {TABS.map(t => (
                <button key={t.id} onClick={() => setTab(t.id)}
                  className={`relative px-4 py-3 text-sm font-medium transition-all
                    duration-300 font-display whitespace-nowrap
                    ${tab === t.id ? 'text-green-400' : 'text-zinc-500 hover:text-zinc-300'}`}>
                  <span className="flex items-center gap-2">
                    <span className={`font-mono text-xs ${tab === t.id ? 'opacity-100' : 'opacity-40'}`}>
                      {t.icon}
                    </span>
                    {t.label}
                  </span>
                  {tab === t.id && (
                    <div className="absolute bottom-0 left-2 right-2 h-[2px] bg-green-400 rounded-full" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </header>

        {/* content */}
        <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8" key={tab}>
          {tab === 'review' && <ReviewPage />}
          {tab === 'how' && <HowItWorksPage />}
          {tab === 'about' && <AboutPage />}
        </main>

        {/* footer */}
        <footer className="border-t border-zinc-900/50 mt-16">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 py-5 flex items-center justify-between">
            <span className="text-zinc-600 font-mono text-xs">pytorch + claude + fastapi</span>
            <span className="text-zinc-600 font-mono text-xs">amrith pusala</span>
          </div>
        </footer>
      </div>
    </div>
  )
}
