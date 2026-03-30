# reviewer.py — LLM-powered code review using Claude API
#
# takes code chunks from the diff parser, sends them to Claude with
# context about the file and surrounding code, and gets back structured
# review comments categorized by severity and type.
#
# the key design decision: we don't send the entire diff to Claude at once.
# instead, we batch chunks by file and send each file's changes together.
# this keeps context tight and prevents the model from getting confused
# by unrelated changes in other files.

import os
import json
import httpx

ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages'
MODEL = 'claude-sonnet-4-20250514'
MAX_TOKENS = 2048


def get_api_key():
  key = os.getenv('ANTHROPIC_API_KEY')
  if not key:
    raise ValueError('ANTHROPIC_API_KEY environment variable is not set')
  return key


REVIEW_SYSTEM_PROMPT = """You are CodeSentry, an expert code reviewer. You review pull request diffs and identify real issues that matter.

Your job is to find:
- BUGS: logic errors, off-by-ones, null/undefined access, race conditions, incorrect comparisons
- SECURITY: SQL injection, XSS, hardcoded secrets, path traversal, insecure deserialization
- PERFORMANCE: O(n^2) in hot paths, unnecessary allocations, missing indexes, N+1 queries
- STYLE: unclear naming, overly complex logic, missing error handling, dead code

Rules:
1. Only flag issues you are confident about. Do not guess or speculate.
2. Be specific. Reference exact line content when pointing out an issue.
3. Explain WHY it's a problem and HOW to fix it.
4. Do NOT comment on formatting, whitespace, import ordering, or minor style preferences.
5. Do NOT praise code or add filler like "looks good overall."
6. If the code is clean, return an empty findings array.

Respond with ONLY a JSON object in this exact format, no markdown fences:
{
  "findings": [
    {
      "type": "bug" | "security" | "performance" | "style",
      "severity": "high" | "medium" | "low",
      "line_content": "the exact line of code with the issue",
      "message": "concise explanation of the problem and suggested fix"
    }
  ]
}"""


def _build_review_prompt(file_path, chunks):
  """build the user prompt for reviewing a file's changes."""
  code_sections = []
  for chunk in chunks:
    section = f"Lines {chunk.start_line}-{chunk.end_line}:\n"

    # include context if available
    if chunk.context_lines:
      section += "// surrounding context:\n"
      for line in chunk.context_lines[:5]:  # limit context
        section += f"  {line}\n"
      section += "\n"

    section += "// added code:\n"
    for line in chunk.added_lines:
      section += f"+ {line}\n"

    code_sections.append(section)

  all_code = '\n---\n'.join(code_sections)

  return f"""Review the following code changes in `{file_path}`:

{all_code}

Identify any bugs, security issues, performance problems, or significant code quality issues. Only flag real problems you are confident about."""


async def review_chunks(chunks_by_file):
  """review code chunks grouped by file using Claude.

  args:
    chunks_by_file: dict mapping file_path -> list of DiffChunk

  returns:
    list of review findings, each with file_path, line, type, severity, message
  """
  api_key = get_api_key()
  all_findings = []

  async with httpx.AsyncClient(timeout=60.0) as client:
    for file_path, chunks in chunks_by_file.items():
      # skip files with too many changes (likely generated or refactored)
      total_lines = sum(c.num_added for c in chunks)
      if total_lines > 500:
        all_findings.append({
          'file_path': file_path,
          'line': chunks[0].start_line,
          'type': 'style',
          'severity': 'low',
          'message': f'This file has {total_lines} added lines. Consider breaking this into smaller PRs for easier review.',
        })
        continue

      # skip very small changes (1-2 lines, likely trivial)
      if total_lines < 3:
        continue

      prompt = _build_review_prompt(file_path, chunks)

      try:
        resp = await client.post(
          ANTHROPIC_API_URL,
          headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
          },
          json={
            'model': MODEL,
            'max_tokens': MAX_TOKENS,
            'system': REVIEW_SYSTEM_PROMPT,
            'messages': [{'role': 'user', 'content': prompt}],
          },
        )

        if resp.status_code != 200:
          print(f'claude API error for {file_path}: {resp.status_code} {resp.text[:200]}')
          continue

        data = resp.json()
        text = ''
        for block in data.get('content', []):
          if block.get('type') == 'text':
            text += block['text']

        # parse the JSON response
        findings = _parse_findings(text, file_path, chunks)
        all_findings.extend(findings)

      except Exception as e:
        print(f'error reviewing {file_path}: {e}')
        continue

  return all_findings


def _parse_findings(response_text, file_path, chunks):
  """parse Claude's JSON response into structured findings."""
  findings = []

  # strip markdown fences if present
  text = response_text.strip()
  if text.startswith('```'):
    text = text.split('\n', 1)[1] if '\n' in text else text[3:]
  if text.endswith('```'):
    text = text[:-3]
  text = text.strip()

  try:
    data = json.loads(text)
  except json.JSONDecodeError:
    # try to extract JSON from the response
    start = text.find('{')
    end = text.rfind('}') + 1
    if start >= 0 and end > start:
      try:
        data = json.loads(text[start:end])
      except json.JSONDecodeError:
        print(f'could not parse Claude response for {file_path}')
        return []
    else:
      return []

  for finding in data.get('findings', []):
    # find the closest line number for this finding
    line_content = finding.get('line_content', '')
    line_num = _find_line_number(line_content, chunks)

    findings.append({
      'file_path': file_path,
      'line': line_num,
      'type': finding.get('type', 'style'),
      'severity': finding.get('severity', 'low'),
      'message': finding.get('message', ''),
      'line_content': line_content,
    })

  return findings


def _find_line_number(line_content, chunks):
  """find the line number in the diff that matches the given content."""
  if not line_content:
    return chunks[0].end_line if chunks else 1

  line_content = line_content.strip()
  for chunk in chunks:
    for i, added_line in enumerate(chunk.added_lines):
      if line_content in added_line.strip():
        return chunk.start_line + i

  # fallback: return the end of the first chunk
  return chunks[0].end_line if chunks else 1


def format_comment(finding):
  """format a finding into a GitHub PR comment body."""
  severity_icons = {
    'high': '\U0001F534',    # red circle
    'medium': '\U0001F7E1',  # yellow circle
    'low': '\U0001F535',     # blue circle
  }
  type_labels = {
    'bug': 'Bug',
    'security': 'Security',
    'performance': 'Performance',
    'style': 'Code Quality',
  }

  icon = severity_icons.get(finding['severity'], '\U0001F535')
  label = type_labels.get(finding['type'], 'Issue')
  severity = finding['severity'].upper()

  comment = f"**{icon} CodeSentry** [{label} / {severity}]\n\n"
  comment += finding['message']

  if finding.get('line_content'):
    comment += f"\n\n```\n{finding['line_content']}\n```"

  return comment
