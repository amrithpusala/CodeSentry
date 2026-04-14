export default function AboutPage() {
  return (
    <div className="space-y-10" style={{ animation: 'fadeIn .4s ease-out' }}>
      <div className="text-center py-6">
        <h2 className="text-2xl font-bold tracking-tight mb-2 font-display">
          About CodeSentry
        </h2>
        <p className="text-zinc-500 text-sm max-w-lg mx-auto">
          An AI code review bot that combines a custom ML classifier with
          LLM analysis to catch bugs in pull requests. Built for the
          ML@Purdue Symposium.
        </p>
      </div>

      {/* why */}
      <div className="bg-zinc-900/20 border border-zinc-800/50 rounded-xl p-6 space-y-3">
        <h3 className="text-sm font-semibold text-green-400 font-display">The Problem</h3>
        <p className="text-zinc-400 text-sm leading-relaxed">
          Copilot Code Review costs $10-19/month and is a black-box LLM wrapper.
          It sends every code change to GPT regardless of risk, wasting API
          calls on trivial changes. There's no custom ML, no transparency,
          and no way to inspect or retrain the model.
        </p>
      </div>

      <div className="bg-zinc-900/20 border border-zinc-800/50 rounded-xl p-6 space-y-3">
        <h3 className="text-sm font-semibold text-green-400 font-display">The Solution</h3>
        <p className="text-zinc-400 text-sm leading-relaxed">
          CodeSentry uses a two-stage pipeline. A custom PyTorch classifier
          trained on 1,200+ real bug-fix commits scores each code chunk in 2ms.
          Only high-risk chunks (above 0.6 threshold) get sent to Claude for
          detailed review. This cuts API costs by 40-60% while maintaining 73%
          bug recall. The LLM acts as a second filter, so missed bugs from the
          classifier still get caught.
        </p>
      </div>

      {/* tech stack */}
      <div>
        <h3 className="text-lg font-semibold mb-3 font-display">Tech Stack</h3>
        <div className="grid grid-cols-2 gap-3">
          {[
            { name: 'FastAPI', role: 'API + Webhooks', icon: 'API' },
            { name: 'PyTorch', role: 'Risk Classifier', icon: 'ML' },
            { name: 'Claude API', role: 'Code Review', icon: 'LLM' },
            { name: 'React + Vite', role: 'Dashboard', icon: 'UI' },
            { name: 'GitHub API', role: 'PR Integration', icon: 'GH' },
            { name: 'Tailwind CSS', role: 'Styling', icon: 'CSS' },
          ].map((t, i) => (
            <div key={i} className="bg-zinc-900/30 border border-zinc-800/50 rounded-xl p-4
              flex items-center gap-3 hover:border-zinc-700/50 transition-colors group">
              <div className="w-9 h-9 rounded-lg bg-zinc-800/80 border border-zinc-700/50
                flex items-center justify-center font-mono text-[10px] font-bold text-zinc-500
                group-hover:text-green-400 group-hover:border-green-500/30 transition-all">
                {t.icon}
              </div>
              <div>
                <div className="text-white text-sm font-semibold">{t.name}</div>
                <div className="text-zinc-600 text-xs">{t.role}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* features */}
      <div>
        <h3 className="text-lg font-semibold mb-3 font-display">Features</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { name: 'Automatic PR Reviews', desc: 'Triggers on PR open via GitHub webhooks' },
            { name: 'Bug Risk Classifier', desc: 'PyTorch model trained on real bug-fix commits' },
            { name: 'Smart Triage', desc: 'Only high-risk code sent to expensive LLM review' },
            { name: 'Inline Comments', desc: 'Findings posted directly on the PR diff' },
            { name: 'Multi-Language', desc: 'Python, JS, TS, Java, Go, Rust, C, and more' },
            { name: 'Snippet Review', desc: 'Paste code in the dashboard for instant analysis' },
          ].map((f, i) => (
            <div key={i} className="bg-zinc-900/30 border border-zinc-800/50 rounded-xl p-4
              hover:border-zinc-700/50 transition-colors">
              <div className="text-white text-sm font-semibold">{f.name}</div>
              <div className="text-zinc-600 text-xs mt-1">{f.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* built by */}
      <div className="bg-zinc-900/20 border border-zinc-800/50 rounded-xl p-6 text-center">
        <div className="font-mono text-2xl mb-2 opacity-20">{'{ }'}</div>
        <h3 className="text-lg font-semibold mb-1 font-display">Built by Amrith Pusala</h3>
        <p className="text-zinc-600 text-sm mb-4">Computer Science @ Purdue University</p>
        <div className="flex justify-center gap-3">
          <a href="https://github.com/amrithpusala/CodeSentry" target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 rounded-lg bg-zinc-900/50 border border-zinc-800/60
              text-zinc-400 text-xs font-mono hover:border-green-500/30 hover:text-green-400 transition-colors">
            github
          </a>
          <a href="https://linkedin.com/in/amrithpusala" target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 rounded-lg bg-zinc-900/50 border border-zinc-800/60
              text-zinc-400 text-xs font-mono hover:border-green-500/30 hover:text-green-400 transition-colors">
            linkedin
          </a>
        </div>
      </div>
    </div>
  )
}
