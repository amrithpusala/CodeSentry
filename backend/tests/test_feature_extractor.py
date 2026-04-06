# test_feature_extractor.py

from app.diff_parser import DiffChunk
from app.feature_extractor import extract_features, CodeFeatures


def _chunk(lines, file_path='app/main.py', start=1):
  return DiffChunk(
    file_path=file_path,
    start_line=start,
    end_line=start + len(lines) - 1,
    added_lines=lines,
    context_lines=[],
  )


def test_basic_extraction():
  chunk = _chunk(['x = 1', 'y = 2', 'return x + y'])
  features = extract_features(chunk)
  assert features.num_added_lines == 3
  assert features.num_returns == 1


def test_detects_sql_injection():
  chunk = _chunk([
    'def get_user(id):',
    '    query = f"SELECT * FROM users WHERE id = {id}"',
    '    return db.execute(query)',
  ])
  features = extract_features(chunk)
  assert features.has_sql_string is True


def test_detects_eval():
  chunk = _chunk(['result = eval(user_input)'])
  features = extract_features(chunk)
  assert features.has_eval_exec is True


def test_detects_hardcoded_secret():
  chunk = _chunk(['api_key = "sk-1234567890abcdef"'])
  features = extract_features(chunk)
  assert features.has_hardcoded_secret is True


def test_detects_shell_command():
  chunk = _chunk(['os.system("rm -rf " + user_path)'])
  features = extract_features(chunk)
  assert features.has_shell_command is True


def test_detects_branches_and_loops():
  chunk = _chunk([
    'if x > 0:',
    '    for item in data:',
    '        if item.valid:',
    '            result.append(item)',
  ])
  features = extract_features(chunk)
  assert features.num_branches == 2
  assert features.num_loops == 1
  assert features.cyclomatic_estimate == 4  # 2 branches + 1 loop + 1


def test_detects_exception_handling():
  chunk = _chunk([
    'try:',
    '    result = risky_call()',
    'except ValueError:',
    '    return None',
  ])
  features = extract_features(chunk)
  assert features.has_exception_handling is True


def test_test_file_detection():
  chunk = _chunk(['assert True'], file_path='tests/test_main.py')
  features = extract_features(chunk)
  assert features.is_test_file is True

  chunk2 = _chunk(['x = 1'], file_path='app/main.py')
  features2 = extract_features(chunk2)
  assert features2.is_test_file is False


def test_file_extension_id():
  py = _chunk(['x = 1'], file_path='app/main.py')
  js = _chunk(['x = 1'], file_path='src/app.js')
  assert extract_features(py).file_extension_id == 1
  assert extract_features(js).file_extension_id == 2


def test_vector_length():
  chunk = _chunk(['x = 1'])
  features = extract_features(chunk)
  vec = features.to_vector()
  assert len(vec) == CodeFeatures.num_features()
  assert all(isinstance(v, float) for v in vec)


def test_long_lines():
  chunk = _chunk(['x = ' + 'a' * 200])
  features = extract_features(chunk)
  assert features.num_long_lines == 1
  assert features.max_line_length > 120


def test_comment_ratio():
  chunk = _chunk([
    '# this is a comment',
    '# another comment',
    'x = 1',
    'y = 2',
  ])
  features = extract_features(chunk)
  assert features.comment_ratio == 0.5


def test_print_debug():
  chunk = _chunk(['print("debug value:", x)'])
  features = extract_features(chunk)
  assert features.has_print_debug is True
