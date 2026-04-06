# collect_data.py — collect training data from real GitHub repositories
#
# strategy: we identify bug-fix commits by their commit messages
# (containing words like "fix", "bug", "patch") and clean commits
# (containing "feat", "refactor", "add"). we extract code features
# from each commit's diff and label them accordingly.
#
# usage:
#   export GITHUB_TOKEN=ghp_your_token_here
#   python ml/collect_data.py --repos 10 --output ml/data/training_data.csv

import argparse
import csv
import os
import re
import sys
import time
import random
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from app.diff_parser import parse_diff, merge_small_chunks
from app.feature_extractor import extract_features, CodeFeatures

GITHUB_API = 'https://api.github.com'

SEED_REPOS = [
  'pallets/flask', 'psf/requests', 'django/django',
  'fastapi/fastapi', 'encode/httpx', 'tiangolo/sqlmodel',
  'pydantic/pydantic', 'python-pillow/Pillow',
  'matplotlib/matplotlib', 'pandas-dev/pandas',
  'scikit-learn/scikit-learn', 'facebook/react',
  'vercel/next.js', 'expressjs/express', 'nodejs/node',
  'vuejs/core', 'sveltejs/svelte', 'gin-gonic/gin',
  'gofiber/fiber', 'spring-projects/spring-boot',
]

BUG_PATTERNS = re.compile(
  r'\b(fix|bug|patch|resolve|crash|error|broken|regression|hotfix'
  r'|null pointer|NPE|race condition|overflow|off.by.one)\b',
  re.IGNORECASE
)

CLEAN_PATTERNS = re.compile(
  r'\b(feat|feature|add|implement|refactor|clean|improve|enhance|optimize)\b',
  re.IGNORECASE
)


def get_headers():
  token = os.getenv('GITHUB_TOKEN')
  if not token:
    raise ValueError('GITHUB_TOKEN env var required')
  return {
    'Authorization': f'token {token}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'CodeSentry/1.0',
  }


def fetch_commits(client, owner, repo, page=1):
  resp = client.get(
    f'{GITHUB_API}/repos/{owner}/{repo}/commits',
    params={'page': page, 'per_page': 50},
    headers=get_headers(), timeout=30.0,
  )
  return resp.json() if resp.status_code == 200 else []


def fetch_commit_diff(client, owner, repo, sha):
  resp = client.get(
    f'{GITHUB_API}/repos/{owner}/{repo}/commits/{sha}',
    headers={**get_headers(), 'Accept': 'application/vnd.github.v3.diff'},
    timeout=30.0,
  )
  return resp.text if resp.status_code == 200 else None


def classify_message(message):
  msg = message.split('\n')[0].lower()
  is_bug = bool(BUG_PATTERNS.search(msg))
  is_clean = bool(CLEAN_PATTERNS.search(msg))
  if is_bug and not is_clean:
    return 'bugfix'
  elif is_clean and not is_bug:
    return 'clean'
  return 'skip'


def process_commit(client, owner, repo, commit, label):
  sha = commit['sha']
  diff_text = fetch_commit_diff(client, owner, repo, sha)
  if not diff_text:
    return []

  chunks = parse_diff(diff_text)
  chunks = merge_small_chunks(chunks)

  samples = []
  for chunk in chunks:
    if chunk.num_added < 3 or chunk.num_added > 200:
      continue
    features = extract_features(chunk)
    samples.append((features.to_vector(), label))
  return samples


def collect_from_repo(client, owner, repo, max_commits=50):
  samples = []
  for page in range(1, 6):
    commits = fetch_commits(client, owner, repo, page=page)
    if not commits:
      break
    for commit in commits:
      msg = commit.get('commit', {}).get('message', '')
      category = classify_message(msg)
      if category == 'bugfix':
        samples.extend(process_commit(client, owner, repo, commit, 1))
      elif category == 'clean':
        samples.extend(process_commit(client, owner, repo, commit, 0))
      time.sleep(0.5)  # respect rate limits
      if len(samples) >= max_commits * 2:
        return samples
  return samples


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--repos', type=int, default=10)
  parser.add_argument('--output', type=str, default='ml/data/training_data.csv')
  parser.add_argument('--commits-per-repo', type=int, default=50)
  parser.add_argument('--seed', type=int, default=42)
  args = parser.parse_args()

  random.seed(args.seed)
  repos = random.sample(SEED_REPOS, min(args.repos, len(SEED_REPOS)))
  os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

  header = CodeFeatures.feature_names() + ['label']
  all_samples = []

  print(f'collecting from {len(repos)} repos\n')

  with httpx.Client() as client:
    for i, repo_full in enumerate(repos):
      owner, repo = repo_full.split('/')
      print(f'[{i+1}/{len(repos)}] {repo_full}...', end=' ', flush=True)
      try:
        samples = collect_from_repo(client, owner, repo, args.commits_per_repo)
        all_samples.extend(samples)
        buggy = sum(1 for _, l in samples if l == 1)
        clean = len(samples) - buggy
        print(f'{len(samples)} samples ({buggy} buggy, {clean} clean)')
      except Exception as e:
        print(f'error: {e}')

  random.shuffle(all_samples)

  with open(args.output, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    for features, label in all_samples:
      writer.writerow(features + [label])

  total = len(all_samples)
  buggy = sum(1 for _, l in all_samples if l == 1)
  print(f'\ndone. {total} samples ({buggy} buggy, {total-buggy} clean)')
  print(f'saved to {args.output}')


if __name__ == '__main__':
  main()
