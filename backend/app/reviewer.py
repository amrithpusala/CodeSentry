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
import re
import json
import httpx
from collections import defaultdict

ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages'
MODEL = 'claude-sonnet-4-20250514'
MAX_TOKENS = 2048


def get_api_key():
  key = os.getenv('ANTHROPIC_API_KEY')
  if not key:
    raise ValueError('ANTHROPIC_API_KEY environment variable is not set')
  return key


REVIEW_SYSTEM_PROMPT = """You are CodeSentry, an expert code reviewer. You review pull request diffs and identify real issues.

Your job is to find:
- BUGS: logic errors, off-by-ones, null/undefined access, race conditions, incorrect comparisons
- SECURITY: SQL injection, XSS, hardcoded secrets, path traversal, insecure deserialization
- PERFORMANCE: O(n^2) in hot paths, unnecessary allocations, missing indexes, N+1 queries
- STYLE: unclear naming, overly complex logic, missing error handling, dead code

Rules:
1. Only flag issues with confidence >= 0.5. Do not guess or speculate.
2. Be specific. Reference exact line content when pointing out an issue.
3. Explain WHY it is a problem. Provide a concrete fix in the suggestion field.
4. Do NOT comment on formatting, whitespace, import ordering, or minor style preferences.
5. Do NOT praise code or add filler. If code is clean, return an empty findings array.
6. When cross-file context is provided, check for interface mismatches, missing caller updates, and inconsistencies across files.

Respond with ONLY a JSON object in this exact format, no markdown fences:
{
  "findings": [
    {
      "type": "bug" | "security" | "performance" | "style",
      "severity": "high" | "medium" | "low",
      "line_content": "the exact line of code with the issue",
      "message": "concise explanation of the problem",
      "suggestion": "concrete fixed code snippet or specific fix instruction",
      "confidence": 0.0 to 1.0
    }
  ]
}"""


_SIG_PATTERN = re.compile(
  r'^(?:[ \t]*)(?:def\s+\w+[^:\n]*:|class\s+\w+[^:\n]*:'
  r'|function\s+\w+[^{\n]*\{'
  r'|(?:export\s+)?(?:async\s+)?function\s+\w+'
  r'|const\s+\w+\s*=\s*(?:async\s+)?\([^)]*\)\s*=>'
  r'|func\s+\w+[^{\n]*\{'
  r'|(?:public|private|protected|internal)\s+\w[\w<>\[\]]+\s+\w+\s*\()',
  re.MULTILINE,
)


def _extract_file_structure(file_content):
  """extract function/class signatures from a full file, capped at 50 lines."""
  matches = _SIG_PATTERN.findall(file_content)
  return '\n'.join(m.strip() for m in matches[:50])


def _build_review_prompt(file_path, chunks, pr_context=None,
                         full_file_structure='', focus_areas=None):
  """build the user prompt for reviewing a file's changes."""
  parts = []

  if pr_context:
    title = pr_context.get('title', '')
    body = (pr_context.get('body') or '')[:400]
    if title:
      parts.append(f'## PR Context\nTitle: {title}')
      if body:
        parts.append(f'Description: {body}')
      parts.append('')

  if pr_context and pr_context.get('changed_files_summary'):
    parts.append(
      '## Other Files Changed in This PR\n'
      + pr_context['changed_files_summary']
    )
    parts.append('')

  if full_file_structure:
    parts.append(
      f'## Full File Structure (`{file_path}`)\n{full_file_structure}'
    )
    parts.append('')

  if focus_areas:
    areas_text = '\n'.join(f'- {a}' for a in focus_areas)
    parts.append(f'## Risk Classifier Focus Areas\nPay special attention to:\n{areas_text}')
    parts.append('')

  code_sections = []
  for chunk in chunks:
    section = f'Lines {chunk.start_line}-{chunk.end_line}:\n'
    if chunk.context_lines:
      section += '// surrounding context:\n'
      for line in chunk.context_lines[:5]:
        section += f'  {line}\n'
      section += '\n'
    section += '// added code:\n'
    for line in chunk.added_lines:
      section += f'+ {line}\n'
    code_sections.append(section)

  parts.append(f'Review the following code changes in `{file_path}`:\n')
  parts.append('\n---\n'.join(code_sections))
  parts.append(
    '\nIdentify bugs, security issues, performance problems, or significant code quality issues. '
    'Only flag real problems with confidence >= 0.5.'
  )

  return '\n'.join(parts)


async def review_chunks(chunks_by_file, pr_context=None,
                        file_structures=None, focus_areas_by_file=None):
  """review code chunks grouped by file using Claude.

  args:
    chunks_by_file: dict mapping file_path -> list of DiffChunk
    pr_context: optional dict with 'title', 'body', 'changed_files_summary'
    file_structures: optional dict mapping file_path -> signature string
    focus_areas_by_file: optional dict mapping file_path -> list[str]

  returns:
    list of review findings, each with file_path, line, type, severity,
    message, line_content, suggestion, confidence
  """
  api_key = get_api_key()
  all_findings = []

  async with httpx.AsyncClient(timeout=60.0) as client:
    for file_path, chunks in chunks_by_file.items():
      total_lines = sum(c.num_added for c in chunks)
      if total_lines > 500:
        all_findings.append({
          'file_path': file_path,
          'line': chunks[0].start_line,
          'type': 'style',
          'severity': 'low',
          'message': f'This file has {total_lines} added lines. Consider breaking this into smaller PRs.',
          'line_content': '',
          'suggestion': '',
          'confidence': 1.0,
        })
        continue

      if total_lines < 3:
        continue

      structure = (file_structures or {}).get(file_path, '')
      focus = (focus_areas_by_file or {}).get(file_path)
      prompt = _build_review_prompt(file_path, chunks, pr_context, structure, focus)

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

        findings = _parse_findings(text, file_path, chunks)
        all_findings.extend(findings)

      except Exception as e:
        print(f'error reviewing {file_path}: {e}')
        continue

  return _group_findings(all_findings)


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
    confidence = float(finding.get('confidence', 1.0))
    if confidence < 0.5:
      continue

    line_content = finding.get('line_content', '')
    line_num = _find_line_number(line_content, chunks)

    findings.append({
      'file_path': file_path,
      'line': line_num,
      'type': finding.get('type', 'style'),
      'severity': finding.get('severity', 'low'),
      'message': finding.get('message', ''),
      'line_content': line_content,
      'suggestion': finding.get('suggestion', ''),
      'confidence': confidence,
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


def _group_findings(findings):
  """group findings with the same pattern into one, annotating repeated locations."""
  groups = defaultdict(list)
  for f in findings:
    key = (f['type'], f['severity'], f['message'][:60])
    groups[key].append(f)

  result = []
  for group in groups.values():
    if len(group) == 1:
      result.append(group[0])
    else:
      merged = dict(group[0])
      locs = [f"line {f['line']} in `{f['file_path']}`" for f in group]
      merged['message'] = (
        f"{merged['message']} [Found in {len(group)} locations: {', '.join(locs)}]"
      )
      result.append(merged)
  return result


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

  if finding.get('suggestion'):
    comment += f"\n\n**Suggested fix:**\n```\n{finding['suggestion']}\n```"

  confidence = finding.get('confidence')
  if confidence is not None and confidence < 0.9:
    comment += f"\n\n*Confidence: {confidence:.0%}*"

  return comment
