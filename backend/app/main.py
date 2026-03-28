# main.py — fastapi app with github webhook handler
# run with: uvicorn app.main:app --reload --port 8000

import os
import time
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.diff_parser import parse_diff, merge_small_chunks
from app.github_client import (
  verify_webhook_signature, fetch_pr_diff, fetch_pr_files,
  post_review_summary,
)

# --- rate limiter ---
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 20
_request_log = defaultdict(list)


def check_rate_limit(client_ip: str):
  now = time.time()
  _request_log[client_ip] = [
    t for t in _request_log[client_ip] if now - t < RATE_LIMIT_WINDOW
  ]
  if len(_request_log[client_ip]) >= RATE_LIMIT_MAX:
    raise HTTPException(status_code=429, detail='rate limit exceeded')
  _request_log[client_ip].append(now)


# --- app setup ---

is_production = os.getenv('CODESENTRY_ENV') == 'production'

app = FastAPI(
  title='CodeSentry API',
  description='AI-powered code review bot for GitHub pull requests',
  version='0.1.0',
  docs_url=None if is_production else '/docs',
  redoc_url=None if is_production else '/redoc',
)

ALLOWED_ORIGINS = [
  'http://localhost:5173',
  'http://localhost:3000',
  'http://127.0.0.1:5173',
]

app.add_middleware(
  CORSMiddleware,
  allow_origins=ALLOWED_ORIGINS,
  allow_methods=['GET', 'POST'],
  allow_headers=['Content-Type'],
)


# --- endpoints ---

@app.get('/')
def root():
  return {'status': 'ok', 'service': 'codesentry-api', 'version': '0.1.0'}


@app.get('/health')
def health():
  return {'status': 'healthy'}


@app.post('/api/webhook/github')
async def github_webhook(request: Request):
  """handle incoming github webhook events.
  triggered when a PR is opened, updated, or synchronized.
  verifies the webhook signature before processing.
  """
  # verify signature
  body = await request.body()
  signature = request.headers.get('X-Hub-Signature-256', '')

  if not verify_webhook_signature(body, signature):
    raise HTTPException(status_code=401, detail='invalid webhook signature')

  event_type = request.headers.get('X-GitHub-Event', '')

  # only process pull request events
  if event_type != 'pull_request':
    return {'status': 'ignored', 'event': event_type}

  payload = await request.json()
  action = payload.get('action', '')

  # only review on opened, synchronize (new commits pushed), or reopened
  if action not in ('opened', 'synchronize', 'reopened'):
    return {'status': 'ignored', 'action': action}

  pr = payload.get('pull_request', {})
  repo = payload.get('repository', {})

  owner = repo.get('owner', {}).get('login', '')
  repo_name = repo.get('name', '')
  pr_number = pr.get('number', 0)
  commit_sha = pr.get('head', {}).get('sha', '')

  if not all([owner, repo_name, pr_number, commit_sha]):
    raise HTTPException(status_code=400, detail='missing PR data in webhook payload')

  # run the review
  result = await run_review(owner, repo_name, pr_number, commit_sha)
  return result


class ManualReviewRequest(BaseModel):
  owner: str = Field(..., description='repo owner (e.g. amrithpusala)')
  repo: str = Field(..., description='repo name (e.g. codesentry)')
  pr_number: int = Field(..., ge=1, description='pull request number')


@app.post('/api/review')
async def manual_review(req: ManualReviewRequest, request: Request):
  """manually trigger a review on a pull request.
  useful for testing without setting up webhooks.
  """
  check_rate_limit(request.client.host)

  # fetch the PR to get the head commit SHA
  import httpx
  token = os.getenv('GITHUB_TOKEN', '')
  async with httpx.AsyncClient() as client:
    resp = await client.get(
      f'https://api.github.com/repos/{req.owner}/{req.repo}/pulls/{req.pr_number}',
      headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'CodeSentry/1.0',
      },
      timeout=30.0,
    )
    if resp.status_code != 200:
      raise HTTPException(status_code=404, detail='PR not found')
    pr_data = resp.json()

  commit_sha = pr_data.get('head', {}).get('sha', '')
  result = await run_review(req.owner, req.repo, req.pr_number, commit_sha)
  return result


async def run_review(owner, repo, pr_number, commit_sha):
  """core review logic: fetch diff, parse chunks, score risk, generate comments.

  this is called by both the webhook handler and the manual review endpoint.
  """
  start = time.time()

  # step 1: fetch the diff
  diff_text = await fetch_pr_diff(owner, repo, pr_number)
  if not diff_text:
    return {'status': 'error', 'detail': 'could not fetch PR diff'}

  # step 2: parse into reviewable chunks
  chunks = parse_diff(diff_text)
  chunks = merge_small_chunks(chunks)

  if not chunks:
    return {
      'status': 'ok',
      'detail': 'no reviewable code changes found',
      'files_checked': 0,
      'chunks': 0,
    }

  # step 3: score each chunk with the risk classifier
  # (placeholder for now, will be implemented in phase 2)
  scored_chunks = []
  for chunk in chunks:
    scored_chunks.append({
      'chunk': chunk,
      'risk_score': 0.5,  # placeholder: all medium risk
      'risk_label': 'medium',
    })

  # step 4: send high-risk chunks to LLM for detailed review
  # (placeholder for now, will be implemented in phase 3)
  review_comments = []
  for sc in scored_chunks:
    if sc['risk_score'] >= 0.6:
      review_comments.append({
        'path': sc['chunk'].file_path,
        'line': sc['chunk'].end_line,
        'body': (
          f'**CodeSentry** (risk: {sc["risk_label"]})\n\n'
          f'This code chunk has {sc["chunk"].num_added} new lines '
          f'starting at line {sc["chunk"].start_line}. '
          f'Detailed LLM review coming in a future update.'
        ),
      })

  # step 5: post the review on the PR
  if review_comments:
    summary = (
      f'## CodeSentry Review\n\n'
      f'Analyzed **{len(chunks)}** code chunks across '
      f'**{len(set(c.file_path for c in chunks))}** files.\n\n'
      f'Found **{len(review_comments)}** chunks that need attention.'
    )

    posted = await post_review_summary(
      owner, repo, pr_number, commit_sha,
      review_comments, summary
    )
  else:
    posted = True

  elapsed = time.time() - start

  return {
    'status': 'ok',
    'pr': f'{owner}/{repo}#{pr_number}',
    'chunks_analyzed': len(chunks),
    'files_checked': len(set(c.file_path for c in chunks)),
    'comments_posted': len(review_comments),
    'review_posted': posted,
    'time_seconds': round(elapsed, 2),
  }
