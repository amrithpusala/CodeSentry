# test_reviewer.py — tests for the review comment formatting and parsing

from app.reviewer import format_comment, _parse_findings, _find_line_number
from app.diff_parser import DiffChunk


def _make_chunk(file_path='test.py', start=1, end=5, lines=None):
  return DiffChunk(
    file_path=file_path,
    start_line=start,
    end_line=end,
    added_lines=lines or ['line1', 'line2', 'line3'],
  )


# --- format_comment ---

def test_format_comment_bug():
  finding = {
    'type': 'bug',
    'severity': 'high',
    'message': 'Possible null pointer dereference',
    'line_content': 'result = data.get("key").strip()',
  }
  comment = format_comment(finding)
  assert 'CodeSentry' in comment
  assert 'Bug' in comment
  assert 'HIGH' in comment
  assert 'null pointer' in comment


def test_format_comment_security():
  finding = {
    'type': 'security',
    'severity': 'high',
    'message': 'SQL injection risk with string formatting',
    'line_content': 'query = f"SELECT * FROM users WHERE id = {user_id}"',
  }
  comment = format_comment(finding)
  assert 'Security' in comment
  assert 'SQL injection' in comment


def test_format_comment_low_severity():
  finding = {
    'type': 'style',
    'severity': 'low',
    'message': 'Consider extracting this into a helper function',
    'line_content': '',
  }
  comment = format_comment(finding)
  assert 'Code Quality' in comment
  assert 'LOW' in comment


# --- _parse_findings ---

def test_parse_findings_valid_json():
  response = '{"findings": [{"type": "bug", "severity": "high", "line_content": "x = None", "message": "potential null"}]}'
  chunks = [_make_chunk(lines=['x = None', 'print(x)'])]
  findings = _parse_findings(response, 'test.py', chunks)
  assert len(findings) == 1
  assert findings[0]['type'] == 'bug'
  assert findings[0]['severity'] == 'high'


def test_parse_findings_empty():
  response = '{"findings": []}'
  chunks = [_make_chunk()]
  findings = _parse_findings(response, 'test.py', chunks)
  assert len(findings) == 0


def test_parse_findings_with_markdown_fences():
  response = '```json\n{"findings": [{"type": "security", "severity": "medium", "line_content": "password = 123", "message": "hardcoded password"}]}\n```'
  chunks = [_make_chunk(lines=['password = 123'])]
  findings = _parse_findings(response, 'test.py', chunks)
  assert len(findings) == 1
  assert findings[0]['type'] == 'security'


def test_parse_findings_garbage_input():
  response = 'this is not json at all'
  chunks = [_make_chunk()]
  findings = _parse_findings(response, 'test.py', chunks)
  assert len(findings) == 0


# --- _find_line_number ---

def test_find_line_number_exact_match():
  chunks = [_make_chunk(start=10, end=12, lines=['def foo():', '    return 42', ''])]
  line = _find_line_number('return 42', chunks)
  assert line == 11  # second line starting from 10


def test_find_line_number_no_match():
  chunks = [_make_chunk(start=10, end=12, lines=['x = 1', 'y = 2'])]
  line = _find_line_number('z = 3', chunks)
  assert line == 12  # fallback to end of first chunk


def test_find_line_number_empty_content():
  chunks = [_make_chunk(start=5, end=8)]
  line = _find_line_number('', chunks)
  assert line == 8
