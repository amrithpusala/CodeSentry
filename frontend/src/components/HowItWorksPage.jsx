export default function HowItWorksPage() {
  return (
    <div className="space-y-10" style={{ animation: 'fadeIn .4s ease-out' }}>
      <div className="text-center py-6">
        <h2 className="text-2xl font-bold tracking-tight mb-2 font-display">
          How It Works
        </h2>
        <p className="text-zinc-500 text-sm max-w-lg mx-auto">
          CodeSentry combines a custom-trained ML classifier with Claude
          for intelligent, cost-efficient code review.
        </p>
      </div>

      {/* pipeline */}
      <div className="flex items-center justify-center gap-2 py-4 flex-wrap">
        {[
          { label: 'PR Opened', sub: 'webhook' },
          null,
          { label: 'Diff Parser', sub: 'extract chunks' },
          null,
          { label: 'Risk Classifier', sub: 'PyTorch, 2ms' },
          null,
          { label: 'Context Builder', sub: 'PR meta + file structure' },
          null,
          { label: 'Claude Review', sub: 'high risk only' },
          null,
          { label: 'PR Comments', sub: 'inline + suggestions' },
        ].map((item, i) =>
          item ? (
            <div key={i} className="bg-zinc-900/50 border border-zinc-800/60 rounded-lg
              px-4 py-2.5 text-center">
              <div className="text-white text-xs font-semibold font-display">{item.label}</div>
              <div className="text-zinc-600 font-mono text-[10px] mt-0.5">{item.sub}</div>
            </div>
          ) : (
            <div key={i} className="text-green-500/40 font-mono text-sm">{'\u2192'}</div>
          )
        )}
      </div>

      {/* steps */}
      <div className="space-y-4">
        {[
          { n: 1, title: 'Diff Parsing',
            desc: 'When a PR is opened, CodeSentry receives a GitHub webhook, fetches the unified diff, and breaks it into reviewable code chunks. Non-code files (configs, lockfiles, markdown) are filtered out. Small adjacent changes are merged into logical units.' },
          { n: 2, title: 'Feature Extraction',
            desc: 'Each code chunk is analyzed for 27 syntax features (size, complexity, risky patterns, code hygiene) plus 5 new semantic features: cross-function call depth, import complexity, error-handling ratio, test coverage presence, and commit history risk. The new features adjust the classifier score without retraining the model.' },
          { n: 3, title: 'Risk Classification',
            desc: 'A PyTorch feedforward network (3 layers, 128 units) trained on 1,200+ real commits scores each chunk from 0 to 1. Semantic signals from step 2 apply post-hoc score adjustments (e.g. +0.10 for files with >50% bug-fix commit history). Chunks above 0.6 are flagged for deep review in under 2ms.' },
          { n: 4, title: 'Context Building',
            desc: 'Before sending to the LLM, CodeSentry fetches the PR title and description, extracts function signatures from the full file (not just the diff), and builds a cross-file summary of all other changed files in the PR. The risk classifier\'s flags become a "focus areas" section in the prompt.' },
          { n: 5, title: 'LLM Review',
            desc: 'High-risk chunks are sent to Claude with the full context package: PR intent, file structure, cross-file signatures, and risk focus areas. Claude checks for interface mismatches across files, not just within each one. Each finding includes a concrete fix suggestion and a confidence score. Findings below 50% confidence are filtered out.' },
          { n: 6, title: 'PR Comments',
            desc: 'Findings are grouped by pattern (e.g. the same issue in 3 files becomes one comment noting all locations), formatted with colored severity indicators, concrete fix suggestions, and confidence scores, then posted as inline PR review comments with a full summary.' },
        ].map((step, i) => (
          <div key={i} className="bg-zinc-900/20 border border-zinc-800/50 rounded-xl p-5
            hover:border-zinc-700/60 transition-colors"
            style={{ animation: `slideUp ${0.2 + i * 0.1}s cubic-bezier(.16,1,.3,1)` }}>
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-lg bg-green-500/10 border border-green-500/30
                flex items-center justify-center font-mono text-xs font-bold text-green-400 shrink-0">
                {step.n}
              </div>
              <div>
                <h3 className="font-semibold text-white text-sm mb-1 font-display">{step.title}</h3>
                <p className="text-zinc-500 text-sm leading-relaxed">{step.desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* classifier stats */}
      <div>
        <h3 className="text-lg font-semibold mb-3 font-display">Classifier Performance</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Accuracy', value: '63.5%' },
            { label: 'Precision', value: '61.8%' },
            { label: 'Recall', value: '73.4%' },
            { label: 'F1 Score', value: '0.67' },
          ].map((stat, i) => (
            <div key={i} className="bg-zinc-900/30 border border-zinc-800/50 rounded-xl p-4 text-center">
              <div className="font-mono text-xl font-bold text-green-400">{stat.value}</div>
              <div className="text-zinc-500 text-xs mt-1 font-display">{stat.label}</div>
            </div>
          ))}
        </div>
        <p className="text-zinc-600 font-mono text-xs mt-3">
          trained on 1,253 samples from 15 open-source repos. high recall prioritized to minimize missed bugs.
        </p>
      </div>
    </div>
  )
}
