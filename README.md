# CodeSentry

An AI-powered code review bot for GitHub that combines a custom-trained bug risk classifier with LLM analysis to catch bugs, security issues, and code quality problems in pull requests.

**How it works:** Install on any GitHub repo. When a PR is opened, CodeSentry fetches the diff, scores each changed chunk with a PyTorch risk classifier, enriches high-risk chunks with cross-file context and PR metadata, then sends them to Claude for detailed review. Inline comments with concrete fix suggestions appear on the PR within seconds.

**Why?** Copilot Code Review costs $10-19/month and is a black-box LLM wrapper. CodeSentry is free, open source, and uses a custom ML model you can inspect, retrain, and improve.

## Features

- **Automatic PR reviews** via GitHub App webhooks (no manual triggers)
- **Custom bug risk classifier** trained on real bug-introducing vs clean commits (PyTorch)
- **Cross-file context awareness** — reviews check function signatures across all changed files and verify interface consistency, not just each file in isolation
- **Semantic feature enrichment** — 5 new signals (cross-function call depth, import complexity, error-handling ratio, test coverage presence, commit history risk) adjust triage scores without retraining the model
- **Smarter LLM prompts** — each review includes the PR title/description, full file structure signatures, risk-classifier focus areas, and a cross-file summary
- **Fix suggestions** — every finding includes a concrete code fix and a confidence score
- **Confidence filtering** — findings below 50% confidence are automatically suppressed
- **Finding grouping** — the same pattern appearing in multiple files is collapsed into one comment noting all locations
- **Smart triage** sends only high-risk code to the LLM, keeping costs low
- **Inline PR comments** with severity labels (bug, security, style, performance)
- **Multi-language** — Python, JS/TS, Java, Go, Rust, C/C++, Ruby, Swift, Kotlin, SQL, and more
- **Snippet review** — paste code in the dashboard for instant analysis without a PR

## Architecture

```
backend/               FastAPI + Python
  app/
    main.py              webhook handler, API routes, run_review orchestration
    github_client.py     GitHub API — diffs, PR metadata, file content, commit history
    diff_parser.py       parse PR diffs into reviewable DiffChunk objects
    feature_extractor.py 27 syntax features + 5 semantic features; enrich_features()
    risk_classifier.py   PyTorch risk scoring + semantic score adjustments + focus areas
    reviewer.py          LLM review — cross-file context, prompts, confidence filtering
  tests/                 62 tests covering all modules

ml/                    training pipeline
  collect_data.py        extract bug-fix commits from GitHub repos
  train.py               PyTorch training with early stopping
  model.py               BugRiskClassifier architecture (3-layer feedforward, 128 units)

frontend/              React + Vite dashboard
  src/
    components/
      ReviewPage.jsx       paste-and-review code snippet UI
      HowItWorksPage.jsx   pipeline explanation
      AboutPage.jsx        features and tech stack
```

## Quick Start

```bash
git clone https://github.com/amrithpusala/codesentry.git
cd codesentry/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# webhook endpoint: POST /api/webhook/github
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/webhook/github` | Receives GitHub PR webhook events |
| POST | `/api/review` | Manually trigger a review on a PR |
| POST | `/api/review-snippet` | Review a code snippet directly |
| POST | `/api/risk-score` | Score a snippet without LLM review |
| GET | `/api/classifier-status` | Check if the ML model is loaded |
| GET | `/health` | Health check |

## ML Pipeline

The bug risk classifier is trained on real commits from open source repositories:

1. **Data collection**: extract commits with bug-fix keywords (fix, patch, revert, regression) vs clean commits (feat, refactor, docs)
2. **Feature extraction**: 27 syntax features per diff chunk — size metrics, complexity indicators, risky pattern detection (SQL strings, eval, hardcoded secrets), and code hygiene signals
3. **Model**: 3-layer PyTorch feedforward network (128→128→64→1, sigmoid output), trained with early stopping on F1
4. **Inference**: each chunk in a PR gets a base risk score from 0 to 1. Five semantic signals then apply post-hoc score adjustments:
   - **Commit history risk**: files with >50% bug-fix commit history get +0.10
   - **No test coverage**: untested files with high external call depth get +0.05
   - **Import churn**: files adding >5 new imports get +0.05
   - **Low error handling**: large changes with few try/except blocks and high call depth get +0.05
5. **Threshold**: adjusted scores above 0.6 are flagged for Claude review; the rest are skipped

## Security

- Webhook payloads are verified using GitHub's HMAC-SHA256 signature
- GitHub App uses minimal permissions (read PRs, write comments)
- No source code is stored on disk (processed in memory only)
- Claude API key and GitHub token are stored as environment variables, never in code
- Rate limiting on all endpoints (20 req/60 sec per IP)

## License

MIT
