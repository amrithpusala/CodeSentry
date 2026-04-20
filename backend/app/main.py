# main.py — fastapi app with github webhook handler
# run with: uvicorn app.main:app --reload --port 8000

import os
import time
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.diff_parser import parse_diff, merge_small_chunks
import asyncio
import re
from app.github_client import (
  verify_webhook_signature, fetch_pr_diff, fetch_pr_files,
  post_review_summary, fetch_pr_metadata, fetch_file_content,
  fetch_commit_messages,
)
from app import risk_classifier

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
  'https://frontend-azure-two-61.vercel.app',
  'https://frontend-r8hiuq5vt-amrithpusalas-projects.vercel.app',
  'https://code-sentry-ai.vercel.app',
]

app.add_middleware(
  CORSMiddleware,
  allow_origins=ALLOWED_ORIGINS,
  allow_methods=['GET', 'POST'],
  allow_headers=['Content-Type'],
)


@app.on_event('startup')
def startup():
  risk_classifier.load_model()


# --- endpoints ---

@app.get('/')
def root():
  return {'status': 'ok', 'service': 'codesentry-api', 'version': '0.2.0'}


@app.get('/api/classifier-status')
def classifier_status():
  return {'loaded': risk_classifier.is_loaded()}


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
  """core review logic: fetch diff, parse chunks, review with Claude, post comments.

  this is called by both the webhook handler and the manual review endpoint.
  """
  from app.reviewer import review_chunks, format_comment, _extract_file_structure
  from app.feature_extractor import extract_features, enrich_features
  from app.risk_classifier import score_chunks_with_context, get_focus_areas

  start = time.time()

  # step 1: fetch diff + PR metadata + changed files list in parallel
  diff_text, pr_meta, pr_files_data = await asyncio.gather(
    fetch_pr_diff(owner, repo, pr_number),
    fetch_pr_metadata(owner, repo, pr_number),
    fetch_pr_files(owner, repo, pr_number),
    return_exceptions=False,
  )

  if not diff_text:
    return {'status': 'error', 'detail': 'could not fetch PR diff'}

  pr_file_paths = [f['filename'] for f in pr_files_data]

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

  # step 3: extract + enrich features for all chunks
  features_map = {id(c): extract_features(c) for c in chunks}

  # fetch commit history for up to 5 unique files in parallel
  unique_files = list({c.file_path for c in chunks})[:5]
  commit_results = await asyncio.gather(
    *[fetch_commit_messages(owner, repo, fp) for fp in unique_files],
    return_exceptions=True,
  )
  commit_msgs_by_file = {
    fp: (msgs if isinstance(msgs, list) else [])
    for fp, msgs in zip(unique_files, commit_results)
  }

  for chunk in chunks:
    msgs = commit_msgs_by_file.get(chunk.file_path, [])
    enrich_features(features_map[id(chunk)], pr_file_paths, chunk.file_path, msgs)

  # step 4: score with semantic adjustments
  scored = score_chunks_with_context(chunks, features_map)

  # split into high-risk (send to LLM) and low-risk (skip)
  high_risk_chunks = [(c, s, l) for c, s, l in scored if s >= risk_classifier.THRESHOLD]
  low_risk_chunks = [(c, s, l) for c, s, l in scored if s < risk_classifier.THRESHOLD]

  # step 5: group high-risk chunks by file for batched LLM review
  chunks_by_file = defaultdict(list)
  for chunk, score, label in high_risk_chunks:
    chunks_by_file[chunk.file_path].append(chunk)

  # step 6: build cross-file context for prompts
  # summarise signatures from each changed file's patch (capped at 10 files)
  changed_files_summary_lines = []
  for fi in pr_files_data[:10]:
    fname = fi.get('filename', '')
    patch = fi.get('patch', '') or ''
    if fname and patch:
      added_sigs = [
        ln[1:].strip() for ln in patch.split('\n')
        if ln.startswith('+') and re.match(r'^\+\s*(def |function |func |class )', ln)
      ]
      if added_sigs:
        changed_files_summary_lines.append(f'`{fname}`: {"; ".join(added_sigs[:3])}')

  pr_context = {
    'title': pr_meta.get('title', ''),
    'body': (pr_meta.get('body') or '')[:500],
    'changed_files_summary': '\n'.join(changed_files_summary_lines),
  }

  # build per-file focus areas from enriched features
  focus_areas_by_file = {}
  for chunk, _, _ in high_risk_chunks:
    feat = features_map.get(id(chunk))
    if feat:
      areas = get_focus_areas(feat)
      if areas:
        existing = focus_areas_by_file.setdefault(chunk.file_path, [])
        for a in areas:
          if a not in existing:
            existing.append(a)

  # fetch full file structure for high-risk files (up to 5, in parallel)
  high_risk_files = list(chunks_by_file.keys())[:5]
  file_contents = await asyncio.gather(
    *[fetch_file_content(owner, repo, fp, commit_sha) for fp in high_risk_files],
    return_exceptions=True,
  )
  file_structures = {
    fp: _extract_file_structure(content)
    for fp, content in zip(high_risk_files, file_contents)
    if isinstance(content, str) and content
  }

  # step 7: send high-risk chunks to Claude for review
  if chunks_by_file:
    findings = await review_chunks(
      chunks_by_file,
      pr_context=pr_context,
      file_structures=file_structures,
      focus_areas_by_file=focus_areas_by_file,
    )
  else:
    findings = []

  # step 5: format findings into GitHub PR comments
  review_comments = []
  for finding in findings:
    review_comments.append({
      'path': finding['file_path'],
      'line': finding['line'],
      'body': format_comment(finding),
    })

  # step 6: post the review on the PR
  files_checked = len(chunks_by_file)
  if review_comments:
    # build summary with finding counts
    bug_count = sum(1 for f in findings if f['type'] == 'bug')
    sec_count = sum(1 for f in findings if f['type'] == 'security')
    perf_count = sum(1 for f in findings if f['type'] == 'performance')
    style_count = sum(1 for f in findings if f['type'] == 'style')
    high_count = sum(1 for f in findings if f['severity'] == 'high')

    summary_parts = [
      f'## CodeSentry Review\n',
      f'Scanned **{len(chunks)}** code chunks across **{files_checked}** files.',
    ]

    if risk_classifier.is_loaded():
      summary_parts.append(
        f'Risk classifier triaged **{len(high_risk_chunks)}** high-risk chunks '
        f'for deep review ({len(low_risk_chunks)} low-risk skipped).\n'
      )

    if high_count > 0:
      summary_parts.append(f'\n**{high_count} high-severity** issues found.\n')

    counts = []
    if bug_count: counts.append(f'{bug_count} bugs')
    if sec_count: counts.append(f'{sec_count} security')
    if perf_count: counts.append(f'{perf_count} performance')
    if style_count: counts.append(f'{style_count} code quality')
    if counts:
      summary_parts.append(f'\nFindings: {", ".join(counts)}')

    summary = '\n'.join(summary_parts)

    posted = await post_review_summary(
      owner, repo, pr_number, commit_sha,
      review_comments, summary
    )
  else:
    # no issues found, post a clean summary
    summary = (
      f'## CodeSentry Review\n\n'
      f'Analyzed **{len(chunks)}** code chunks across **{files_checked}** files.\n\n'
      f'No issues found. Code looks clean.'
    )
    await post_review_summary(
      owner, repo, pr_number, commit_sha,
      [], summary
    )
    posted = True

  elapsed = time.time() - start

  return {
    'status': 'ok',
    'pr': f'{owner}/{repo}#{pr_number}',
    'chunks_analyzed': len(chunks),
    'files_checked': files_checked,
    'findings': len(findings),
    'comments_posted': len(review_comments),
    'review_posted': posted,
    'time_seconds': round(elapsed, 2),
    'triage': {
      'total_chunks': len(chunks),
      'high_risk': len(high_risk_chunks),
      'low_risk_skipped': len(low_risk_chunks),
      'classifier_loaded': risk_classifier.is_loaded(),
    },
    'breakdown': {
      'bugs': sum(1 for f in findings if f['type'] == 'bug'),
      'security': sum(1 for f in findings if f['type'] == 'security'),
      'performance': sum(1 for f in findings if f['type'] == 'performance'),
      'style': sum(1 for f in findings if f['type'] == 'style'),
    }
  }


# --- snippet review (for testing and frontend) ---

class SnippetReviewRequest(BaseModel):
  code: str = Field(..., max_length=10000,
                    description='code to review')
  language: str = Field(default='python',
                        description='programming language')
  filename: str = Field(default='snippet.py',
                        description='filename for context')


@app.post('/api/review-snippet')
async def review_snippet(req: SnippetReviewRequest, request: Request):
  """review a code snippet directly without a GitHub PR.
  useful for testing the review engine or building a frontend.
  """
  check_rate_limit(request.client.host)

  from app.diff_parser import DiffChunk
  from app.reviewer import review_chunks, format_comment

  # wrap the snippet as a fake diff chunk
  lines = req.code.split('\n')
  chunk = DiffChunk(
    file_path=req.filename,
    start_line=1,
    end_line=len(lines),
    added_lines=lines,
    context_lines=[],
  )

  start = time.time()
  findings = await review_chunks({req.filename: [chunk]})
  elapsed = time.time() - start

  return {
    'status': 'ok',
    'findings': [
      {
        'type': f['type'],
        'severity': f['severity'],
        'message': f['message'],
        'line': f['line'],
        'line_content': f.get('line_content', ''),
      }
      for f in findings
    ],
    'total_findings': len(findings),
    'time_seconds': round(elapsed, 2),
  }


# --- risk scoring endpoint ---

class RiskScoreRequest(BaseModel):
  code: str = Field(..., max_length=10000, description='code to score')
  filename: str = Field(default='snippet.py', description='filename for context')


@app.post('/api/risk-score')
async def risk_score(req: RiskScoreRequest, request: Request):
  """score a code snippet for bug risk without triggering a full LLM review.
  returns the risk score, label, and top risk factors.
  """
  check_rate_limit(request.client.host)

  from app.diff_parser import DiffChunk

  lines = req.code.split('\n')
  chunk = DiffChunk(
    file_path=req.filename,
    start_line=1,
    end_line=len(lines),
    added_lines=lines,
  )

  result = risk_classifier.score_chunks([chunk])

  return {
    'risk_score': result['risk_score'],
    'risk_label': result['risk_label'],
    'risk_factors': result['risk_factors'],
    'would_trigger_llm': result['risk_score'] >= risk_classifier.RISK_THRESHOLD,
    'threshold': risk_classifier.RISK_THRESHOLD,
    'features': result['features'],
  }
