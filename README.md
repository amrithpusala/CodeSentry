# CodeSentry

An AI-powered code review bot for GitHub that combines a custom-trained bug risk classifier with LLM analysis to catch bugs, security issues, and code quality problems in pull requests.

**How it works:** Install on any GitHub repo. When a PR is opened, CodeSentry fetches the diff, scores each changed function with a PyTorch risk classifier trained on 100K+ real bug-fix commits, and sends high-risk code to Claude for detailed review. Comments appear inline on the PR within seconds.

**Why?** Copilot Code Review costs $10-19/month and is a black-box LLM wrapper. CodeSentry is free, open source, and uses a custom ML model you can inspect, retrain, and improve.

## Features

- **Automatic PR reviews** via GitHub App webhooks (no manual triggers)
- **Custom bug risk classifier** trained on real bug-introducing vs clean commits (PyTorch)
- **LLM-powered review comments** with context-aware feedback via Claude API
- **Smart triage** sends only high-risk code to the LLM, keeping costs low
- **Inline PR comments** with severity labels (bug, security, style, performance)
- **Repository-aware context** through code embeddings for project-specific feedback

## Architecture

```
backend/               FastAPI + Python
  app/
    main.py              webhook handler, API routes
    github_client.py     GitHub API interactions (fetch diffs, post comments)
    diff_parser.py       parse PR diffs into reviewable code chunks
    risk_classifier.py   PyTorch bug risk scoring
    reviewer.py          LLM review orchestration (Claude API)
    models.py            request/response schemas
  tests/

ml/                    training pipeline
  collect_data.py        extract bug-fix commits from GitHub repos
  prepare_dataset.py     label and encode training data
  train.py               fine-tune code risk classifier
  evaluate.py            benchmark precision, recall, F1
  model.py               model architecture (CodeBERT-based)

frontend/              React dashboard (optional)
  src/
    components/          review history, settings, analytics
```

## Quick Start

```bash
git clone https://github.com/amrithpusala/codesentry.git
cd codesentry

# backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# the webhook endpoint will be at POST /api/webhook/github
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/webhook/github` | Receives GitHub PR webhook events |
| POST | `/api/review` | Manually trigger a review on a PR |
| GET | `/api/reviews/{owner}/{repo}/{pr}` | Get review results for a PR |
| GET | `/health` | Health check |

## Tech Stack

| Layer | Tech |
|-------|------|
| API | FastAPI (Python) |
| ML Model | PyTorch, CodeBERT (code risk classification) |
| LLM | Claude API (review comment generation) |
| GitHub Integration | GitHub App (webhooks + REST API) |
| Frontend | React, Vite, Tailwind CSS |
| Hosting | Render (backend), Vercel (frontend) |

## ML Pipeline

The bug risk classifier is trained on real commits from open source repositories:

1. **Data collection**: extract commits that were later reverted or fixed (bug-introducing) vs commits that remained stable (clean)
2. **Encoding**: code diffs are tokenized using CodeBERT's tokenizer into 512-token sequences
3. **Model**: CodeBERT base model fine-tuned with a classification head for binary prediction (buggy vs clean)
4. **Inference**: each changed function in a PR gets a risk score from 0 to 1. Scores above 0.6 trigger detailed LLM review.

## Security

- Webhook payloads are verified using GitHub's HMAC-SHA256 signature
- GitHub App uses minimal permissions (read PRs, write comments)
- No source code is stored on disk (processed in memory only)
- Claude API key is stored as an environment variable, never in code
- Rate limiting on all endpoints

## License

MIT
