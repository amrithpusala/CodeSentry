# test_semantic_features.py — tests for new semantic features in feature_extractor

from app.diff_parser import DiffChunk
from app.feature_extractor import extract_features, enrich_features, CodeFeatures


def _chunk(lines, file_path='app/utils.py', start=1):
  return DiffChunk(
    file_path=file_path,
    start_line=start,
    end_line=start + len(lines) - 1,
    added_lines=lines,
    context_lines=[],
  )


# --- cross_function_calls ---

def test_cross_function_calls_counts_external():
  chunk = _chunk([
    'result = requests.get(url)',
    'data = json.loads(result.text)',
    'parsed = parse_data(data)',
  ])
  features = extract_features(chunk)
  assert features.cross_function_calls >= 3


def test_cross_function_calls_excludes_locally_defined():
  chunk = _chunk([
    'def helper(x):',
    '    return helper(x - 1)',   # call to locally defined function
  ])
  features = extract_features(chunk)
  # 'helper' is defined in this chunk so shouldn't inflate cross_function_calls
  assert features.cross_function_calls == 0


def test_cross_function_calls_excludes_builtins():
  chunk = _chunk([
    'result = sorted(items)',
    'n = len(items)',
    'vals = list(range(n))',
  ])
  features = extract_features(chunk)
  assert features.cross_function_calls == 0


# --- import_complexity ---

def test_import_complexity_counts_imports():
  chunk = _chunk([
    'import os',
    'import sys',
    'from pathlib import Path',
    'x = 1',
  ])
  features = extract_features(chunk)
  assert features.import_complexity == 3


def test_import_complexity_zero_for_no_imports():
  chunk = _chunk(['x = 1', 'y = 2'])
  features = extract_features(chunk)
  assert features.import_complexity == 0


# --- error_handling_ratio ---

def test_error_handling_ratio_with_try_except():
  lines = ['try:', '    x = risky()', 'except ValueError:', '    x = 0'] + ['y = 1'] * 6
  chunk = _chunk(lines)
  features = extract_features(chunk)
  # 2 keywords (try, except) out of 10 lines = 0.2
  assert abs(features.error_handling_ratio - 0.2) < 0.01


def test_error_handling_ratio_zero_when_none():
  chunk = _chunk(['x = 1', 'y = x + 2', 'return y'])
  features = extract_features(chunk)
  assert features.error_handling_ratio == 0.0


# --- enrich_features: has_test_coverage ---

def test_enrich_sets_has_test_coverage_true():
  chunk = _chunk(['x = 1'], file_path='app/utils.py')
  features = extract_features(chunk)
  enrich_features(features, ['tests/test_utils.py', 'app/utils.py'], 'app/utils.py', [])
  assert features.has_test_coverage is True


def test_enrich_sets_has_test_coverage_false_when_missing():
  chunk = _chunk(['x = 1'], file_path='app/utils.py')
  features = extract_features(chunk)
  enrich_features(features, ['app/utils.py', 'app/main.py'], 'app/utils.py', [])
  assert features.has_test_coverage is False


def test_enrich_test_coverage_matches_spec_prefix():
  chunk = _chunk(['x = 1'], file_path='src/parser.js')
  features = extract_features(chunk)
  enrich_features(features, ['spec_parser.js'], 'src/parser.js', [])
  assert features.has_test_coverage is True


# --- enrich_features: commit_history_risk ---

def test_enrich_commit_history_risk_ratio():
  msgs = ['fix null pointer', 'fix login bug', 'fix regression', 'add feature', 'refactor']
  chunk = _chunk(['x = 1'])
  features = extract_features(chunk)
  enrich_features(features, [], 'app/utils.py', msgs)
  assert abs(features.commit_history_risk - 0.6) < 0.001


def test_enrich_commit_history_risk_zero_for_empty():
  chunk = _chunk(['x = 1'])
  features = extract_features(chunk)
  enrich_features(features, [], 'app/utils.py', [])
  assert features.commit_history_risk == 0.0


def test_enrich_commit_history_risk_clean_history():
  msgs = ['feat: add auth', 'refactor: clean up', 'docs: update readme']
  chunk = _chunk(['x = 1'])
  features = extract_features(chunk)
  enrich_features(features, [], 'app/utils.py', msgs)
  assert features.commit_history_risk == 0.0


# --- to_vector still returns 27 elements after new fields ---

def test_to_vector_length_unchanged_after_enrichment():
  chunk = _chunk([
    'import os',
    'result = requests.get(url)',
    'try:',
    '    pass',
    'except:',
    '    pass',
  ])
  features = extract_features(chunk)
  enrich_features(features, [], 'app/utils.py', ['fix crash'])
  vec = features.to_vector()
  assert len(vec) == 27
  assert len(vec) == CodeFeatures.num_features()
  assert all(isinstance(v, float) for v in vec)
