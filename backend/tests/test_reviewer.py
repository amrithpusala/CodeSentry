# test_reviewer.py — tests for the review comment formatting and parsing

from app.reviewer import format_comment, _parse_findings, _find_line_number, _group_findings, _extract_file_structure
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


# --- confidence filtering ---

def test_parse_findings_filters_low_confidence():
  response = '{"findings": [{"type": "bug", "severity": "high", "line_content": "x = None", "message": "risk", "suggestion": "check x", "confidence": 0.3}]}'
  chunks = [_make_chunk(lines=['x = None', 'print(x)'])]
  findings = _parse_findings(response, 'test.py', chunks)
  assert len(findings) == 0


def test_parse_findings_keeps_high_confidence():
  response = '{"findings": [{"type": "security", "severity": "high", "line_content": "eval(x)", "message": "eval risk", "suggestion": "use ast.literal_eval", "confidence": 0.9}]}'
  chunks = [_make_chunk(lines=['eval(x)'])]
  findings = _parse_findings(response, 'test.py', chunks)
  assert len(findings) == 1
  assert findings[0]['suggestion'] == 'use ast.literal_eval'
  assert findings[0]['confidence'] == 0.9


def test_parse_findings_default_confidence_kept():
  # when confidence field is absent, defaults to 1.0 (kept)
  response = '{"findings": [{"type": "bug", "severity": "medium", "line_content": "x = 1", "message": "issue"}]}'
  chunks = [_make_chunk(lines=['x = 1'])]
  findings = _parse_findings(response, 'test.py', chunks)
  assert len(findings) == 1
  assert findings[0]['confidence'] == 1.0


# --- suggestion rendering in format_comment ---

def test_format_comment_includes_suggestion():
  finding = {
    'type': 'security',
    'severity': 'high',
    'message': 'eval is dangerous',
    'line_content': 'eval(user_input)',
    'suggestion': 'use ast.literal_eval(user_input)',
    'confidence': 0.9,
  }
  comment = format_comment(finding)
  assert 'Suggested fix' in comment
  assert 'ast.literal_eval' in comment


def test_format_comment_no_suggestion_field_ok():
  finding = {
    'type': 'bug',
    'severity': 'medium',
    'message': 'null pointer risk',
    'line_content': 'x.strip()',
  }
  comment = format_comment(finding)
  assert 'CodeSentry' in comment
  assert 'Suggested fix' not in comment


def test_format_comment_shows_confidence_when_below_90pct():
  finding = {
    'type': 'style',
    'severity': 'low',
    'message': 'possible issue',
    'line_content': '',
    'confidence': 0.65,
  }
  comment = format_comment(finding)
  assert 'Confidence' in comment
  assert '65%' in comment


# --- _group_findings ---

def test_group_findings_merges_duplicates():
  findings = [
    {'type': 'bug', 'severity': 'high', 'message': 'null pointer dereference found', 'file_path': 'a.py', 'line': 1, 'line_content': '', 'suggestion': '', 'confidence': 0.9},
    {'type': 'bug', 'severity': 'high', 'message': 'null pointer dereference found', 'file_path': 'b.py', 'line': 5, 'line_content': '', 'suggestion': '', 'confidence': 0.8},
    {'type': 'bug', 'severity': 'high', 'message': 'null pointer dereference found', 'file_path': 'c.py', 'line': 9, 'line_content': '', 'suggestion': '', 'confidence': 0.7},
  ]
  grouped = _group_findings(findings)
  assert len(grouped) == 1
  assert '3 locations' in grouped[0]['message']


def test_group_findings_keeps_unique():
  findings = [
    {'type': 'bug', 'severity': 'high', 'message': 'null pointer', 'file_path': 'a.py', 'line': 1, 'line_content': '', 'suggestion': '', 'confidence': 0.9},
    {'type': 'security', 'severity': 'high', 'message': 'sql injection', 'file_path': 'a.py', 'line': 2, 'line_content': '', 'suggestion': '', 'confidence': 0.9},
  ]
  grouped = _group_findings(findings)
  assert len(grouped) == 2


# --- _extract_file_structure ---

def test_extract_file_structure_python():
  content = 'import os\n\ndef foo(x):\n    pass\n\nclass Bar:\n    def method(self):\n        pass\n'
  structure = _extract_file_structure(content)
  assert 'def foo' in structure
  assert 'class Bar' in structure


def test_extract_file_structure_empty_for_blank():
  assert _extract_file_structure('') == ''
