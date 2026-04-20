# github_client.py — interact with the github API
#
# handles two things:
#   1. fetching PR diffs (what code changed)
#   2. posting review comments back on the PR
#
# uses httpx for async HTTP requests instead of PyGithub
# because we need async support inside FastAPI endpoints.

import os
import hmac
import hashlib
import base64
import httpx

GITHUB_API = 'https://api.github.com'


def get_github_token():
  """get the github token from environment variables."""
  token = os.getenv('GITHUB_TOKEN')
  if not token:
    raise ValueError('GITHUB_TOKEN environment variable is not set')
  return token


def get_webhook_secret():
  """get the webhook secret for signature verification."""
  return os.getenv('GITHUB_WEBHOOK_SECRET', '')


def verify_webhook_signature(payload_body, signature_header):
  """verify that the webhook payload came from github.
  github signs each webhook with HMAC-SHA256 using your secret.
  if the signature doesn't match, the request is forged.
  """
  secret = get_webhook_secret()
  if not secret:
    # if no secret is configured, skip verification (dev mode only)
    return True

  if not signature_header:
    return False

  # github sends the signature as "sha256=<hex digest>"
  expected_sig = 'sha256=' + hmac.new(
    secret.encode('utf-8'),
    payload_body,
    hashlib.sha256
  ).hexdigest()

  return hmac.compare_digest(expected_sig, signature_header)


async def fetch_pr_diff(owner, repo, pr_number):
  """fetch the unified diff for a pull request.

  returns the raw diff text or None if the request fails.
  """
  token = get_github_token()
  url = f'{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}'

  async with httpx.AsyncClient() as client:
    resp = await client.get(
      url,
      headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3.diff',
        'User-Agent': 'CodeSentry/1.0',
      },
      timeout=30.0,
    )

    if resp.status_code == 200:
      return resp.text
    else:
      print(f'failed to fetch PR diff: {resp.status_code} {resp.text[:200]}')
      return None


async def fetch_pr_files(owner, repo, pr_number):
  """fetch the list of changed files in a PR with their patches."""
  token = get_github_token()
  url = f'{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files'

  async with httpx.AsyncClient() as client:
    resp = await client.get(
      url,
      headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'CodeSentry/1.0',
      },
      timeout=30.0,
    )

    if resp.status_code == 200:
      return resp.json()
    else:
      print(f'failed to fetch PR files: {resp.status_code}')
      return []


async def fetch_pr_metadata(owner, repo, pr_number):
  """fetch PR title, description, and branch info.

  returns dict with 'title', 'body', 'base_branch' keys, or {} on failure.
  """
  token = get_github_token()
  url = f'{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}'

  async with httpx.AsyncClient() as client:
    resp = await client.get(
      url,
      headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'CodeSentry/1.0',
      },
      timeout=30.0,
    )

    if resp.status_code == 200:
      data = resp.json()
      return {
        'title': data.get('title', ''),
        'body': data.get('body') or '',
        'base_branch': data.get('base', {}).get('ref', ''),
      }
    else:
      print(f'failed to fetch PR metadata: {resp.status_code}')
      return {}


async def fetch_file_content(owner, repo, file_path, ref):
  """fetch the raw content of a file at a given commit ref.

  returns decoded file content string, or '' on failure or if file > 100 KB.
  """
  token = get_github_token()
  url = f'{GITHUB_API}/repos/{owner}/{repo}/contents/{file_path}'

  async with httpx.AsyncClient() as client:
    resp = await client.get(
      url,
      params={'ref': ref},
      headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'CodeSentry/1.0',
      },
      timeout=30.0,
    )

    if resp.status_code == 200:
      data = resp.json()
      if data.get('size', 0) > 100_000:
        return ''
      content = data.get('content', '')
      try:
        return base64.b64decode(content).decode('utf-8', errors='replace')
      except Exception:
        return ''
    else:
      return ''


async def fetch_commit_messages(owner, repo, file_path, limit=20):
  """fetch the last `limit` commit messages that touched a specific file.

  returns list of commit message strings, or [] on failure.
  """
  token = get_github_token()
  url = f'{GITHUB_API}/repos/{owner}/{repo}/commits'

  async with httpx.AsyncClient() as client:
    resp = await client.get(
      url,
      params={'path': file_path, 'per_page': limit},
      headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'CodeSentry/1.0',
      },
      timeout=30.0,
    )

    if resp.status_code == 200:
      return [c['commit']['message'] for c in resp.json()]
    else:
      print(f'failed to fetch commit history for {file_path}: {resp.status_code}')
      return []


async def post_review_comment(owner, repo, pr_number, body, commit_sha,
                               path=None, line=None):
  """post a review comment on a pull request.

  if path and line are provided, the comment is posted inline on the diff.
  otherwise, it's posted as a general PR comment.
  """
  token = get_github_token()

  if path and line:
    # inline review comment
    url = f'{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/reviews'
    payload = {
      'commit_id': commit_sha,
      'body': 'CodeSentry automated review',
      'event': 'COMMENT',
      'comments': [{
        'path': path,
        'line': line,
        'body': body,
      }],
    }
  else:
    # general PR comment
    url = f'{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments'
    payload = {'body': body}

  async with httpx.AsyncClient() as client:
    resp = await client.post(
      url,
      json=payload,
      headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'CodeSentry/1.0',
      },
      timeout=30.0,
    )

    if resp.status_code in (200, 201):
      return True
    else:
      print(f'failed to post comment: {resp.status_code} {resp.text[:200]}')
      return False


async def post_review_summary(owner, repo, pr_number, commit_sha,
                                comments, summary_body):
  """post a full review with multiple inline comments and a summary.

  args:
    comments: list of dicts with 'path', 'line', 'body' keys
    summary_body: the top-level review summary text
  """
  token = get_github_token()
  url = f'{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/reviews'

  payload = {
    'commit_id': commit_sha,
    'body': summary_body,
    'event': 'COMMENT',
    'comments': comments,
  }

  async with httpx.AsyncClient() as client:
    resp = await client.post(
      url,
      json=payload,
      headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'CodeSentry/1.0',
      },
      timeout=30.0,
    )

    if resp.status_code in (200, 201):
      return True
    else:
      print(f'failed to post review: {resp.status_code} {resp.text[:200]}')
      return False
