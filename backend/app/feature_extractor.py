# feature_extractor.py — extract code features from diff chunks
#
# the classifier needs numeric features to score risk. we extract
# 28 features from each code chunk covering:
#   - size metrics (lines added, deleted, functions changed)
#   - complexity indicators (nesting depth, branch count, loop count)
#   - risky pattern detection (eval, exec, SQL strings, hardcoded secrets)
#   - error handling signals (try/except, assertions)
#   - code hygiene (comment ratio, long lines, magic numbers)
#
# these features are language-aware but work across Python, JS, Java,
# Go, and most C-family languages.

import re
from dataclasses import dataclass


@dataclass
class CodeFeatures:
  # size
  num_added_lines: int = 0
  num_context_lines: int = 0
  avg_line_length: float = 0.0
  max_line_length: int = 0
  num_functions_changed: int = 0

  # complexity
  max_nesting_depth: int = 0
  num_branches: int = 0       # if/else/elif/switch/case
  num_loops: int = 0          # for/while/do
  num_returns: int = 0
  num_assignments: int = 0
  cyclomatic_estimate: int = 0  # branches + loops + 1

  # risky patterns
  has_eval_exec: bool = False
  has_sql_string: bool = False
  has_shell_command: bool = False
  has_hardcoded_secret: bool = False
  has_todo_fixme: bool = False
  has_type_cast: bool = False
  has_null_check: bool = False
  has_exception_handling: bool = False
  has_file_io: bool = False
  has_network_call: bool = False

  # code hygiene
  comment_ratio: float = 0.0
  num_long_lines: int = 0     # lines > 120 chars
  num_magic_numbers: int = 0
  has_print_debug: bool = False

  # file context
  is_test_file: bool = False
  file_extension_id: int = 0  # numeric encoding of file type

  # semantic features — NOT in to_vector (model compat); used for score adjustment + prompts
  cross_function_calls: int = 0    # calls to functions not defined in this chunk
  import_complexity: int = 0       # new import statements added
  error_handling_ratio: float = 0.0  # try/except keywords / total added lines
  has_test_coverage: bool = False  # a test file for this source file exists in the PR
  commit_history_risk: float = 0.0  # fraction of recent commits that are bug fixes

  def to_vector(self):
    """convert to a flat list of floats for the classifier."""
    return [
      float(self.num_added_lines),
      float(self.num_context_lines),
      self.avg_line_length,
      float(self.max_line_length),
      float(self.num_functions_changed),
      float(self.max_nesting_depth),
      float(self.num_branches),
      float(self.num_loops),
      float(self.num_returns),
      float(self.num_assignments),
      float(self.cyclomatic_estimate),
      float(self.has_eval_exec),
      float(self.has_sql_string),
      float(self.has_shell_command),
      float(self.has_hardcoded_secret),
      float(self.has_todo_fixme),
      float(self.has_type_cast),
      float(self.has_null_check),
      float(self.has_exception_handling),
      float(self.has_file_io),
      float(self.has_network_call),
      self.comment_ratio,
      float(self.num_long_lines),
      float(self.num_magic_numbers),
      float(self.has_print_debug),
      float(self.is_test_file),
      float(self.file_extension_id),
    ]

  @staticmethod
  def feature_names():
    return [
      'num_added_lines', 'num_context_lines', 'avg_line_length',
      'max_line_length', 'num_functions_changed', 'max_nesting_depth',
      'num_branches', 'num_loops', 'num_returns', 'num_assignments',
      'cyclomatic_estimate', 'has_eval_exec', 'has_sql_string',
      'has_shell_command', 'has_hardcoded_secret', 'has_todo_fixme',
      'has_type_cast', 'has_null_check', 'has_exception_handling',
      'has_file_io', 'has_network_call', 'comment_ratio',
      'num_long_lines', 'num_magic_numbers', 'has_print_debug',
      'is_test_file', 'file_extension_id',
    ]

  @staticmethod
  def num_features():
    return 27


EXTENSION_MAP = {
  '.py': 1, '.js': 2, '.jsx': 2, '.ts': 3, '.tsx': 3,
  '.java': 4, '.go': 5, '.rs': 6, '.c': 7, '.cpp': 7,
  '.h': 7, '.hpp': 7, '.cs': 8, '.rb': 9, '.php': 10,
  '.swift': 11, '.kt': 12, '.scala': 13, '.sql': 14,
}

# patterns that indicate risky code
EVAL_PATTERNS = re.compile(r'\b(eval|exec|compile)\s*\(', re.IGNORECASE)
SQL_PATTERNS = re.compile(r'(SELECT|INSERT|UPDATE|DELETE|DROP)\s+.*(FROM|INTO|SET|TABLE)', re.IGNORECASE)
SQL_FSTRING = re.compile(r'f["\'].*?(SELECT|INSERT|UPDATE|DELETE)', re.IGNORECASE)
SHELL_PATTERNS = re.compile(r'\b(os\.system|subprocess\.(call|run|Popen)|exec\(|child_process)', re.IGNORECASE)
SECRET_PATTERNS = re.compile(r'(password|secret|api_key|token|auth)\s*=\s*["\'][^"\']{4,}', re.IGNORECASE)
TODO_PATTERNS = re.compile(r'\b(TODO|FIXME|HACK|XXX|BUG)\b', re.IGNORECASE)
CAST_PATTERNS = re.compile(r'\b(int|float|str|bool|Number|parseInt|parseFloat)\s*\(', re.IGNORECASE)
NULL_PATTERNS = re.compile(r'(is None|== None|!= None|=== null|!== null|== null|!= null|\?\?)', re.IGNORECASE)
EXCEPTION_PATTERNS = re.compile(r'\b(try|except|catch|finally|throw|raise)\b', re.IGNORECASE)
FILE_IO_PATTERNS = re.compile(r'\b(open\(|readFile|writeFile|readFileSync|fs\.|fopen|fwrite)', re.IGNORECASE)
NETWORK_PATTERNS = re.compile(r'\b(fetch\(|requests\.|http\.|axios\.|urllib|httpx|curl)', re.IGNORECASE)
PRINT_DEBUG = re.compile(r'\b(print\(|console\.log|System\.out\.print|fmt\.Print|println!)', re.IGNORECASE)
MAGIC_NUMBER = re.compile(r'(?<![a-zA-Z_])\b(?!0\b|1\b|2\b|100\b|200\b|404\b|500\b)\d{2,}\b(?!\.\d)')

# function definition patterns across languages
FUNC_PATTERNS = re.compile(
  r'(def\s+\w+|function\s+\w+|func\s+\w+|fn\s+\w+|\w+\s*=\s*(async\s+)?function'
  r'|public\s+\w+\s+\w+\s*\(|private\s+\w+\s+\w+\s*\(|const\s+\w+\s*=\s*\()',
  re.IGNORECASE
)

# branch and loop patterns
BRANCH_PATTERNS = re.compile(r'\b(if|else if|elif|else|switch|case|when)\b')
LOOP_PATTERNS = re.compile(r'\b(for|while|do|foreach|\.forEach|\.map|\.filter)\b')

# comment patterns
COMMENT_PATTERNS = re.compile(r'(^\s*#|^\s*//|^\s*/\*|\*/\s*$|^\s*\*)')


def extract_features(chunk):
  """extract features from a DiffChunk object.

  args:
    chunk: a DiffChunk with file_path, added_lines, context_lines

  returns:
    CodeFeatures dataclass
  """
  features = CodeFeatures()
  lines = chunk.added_lines
  all_lines = lines + chunk.context_lines

  # size metrics
  features.num_added_lines = len(lines)
  features.num_context_lines = len(chunk.context_lines)

  if lines:
    lengths = [len(line) for line in lines]
    features.avg_line_length = sum(lengths) / len(lengths)
    features.max_line_length = max(lengths) if lengths else 0
    features.num_long_lines = sum(1 for l in lengths if l > 120)
  
  # file context
  ext = '.' + chunk.file_path.rsplit('.', 1)[-1] if '.' in chunk.file_path else ''
  features.file_extension_id = EXTENSION_MAP.get(ext, 0)
  features.is_test_file = ('test' in chunk.file_path.lower() or
                            'spec' in chunk.file_path.lower())

  code_text = '\n'.join(lines)
  all_text = '\n'.join(all_lines)

  # function count
  features.num_functions_changed = len(FUNC_PATTERNS.findall(code_text))

  # complexity
  features.num_branches = len(BRANCH_PATTERNS.findall(code_text))
  features.num_loops = len(LOOP_PATTERNS.findall(code_text))
  features.num_returns = code_text.count('return ')
  features.num_assignments = code_text.count(' = ') + code_text.count(' += ') + code_text.count(' -= ')
  features.cyclomatic_estimate = features.num_branches + features.num_loops + 1

  # nesting depth (count leading whitespace changes)
  max_indent = 0
  for line in lines:
    stripped = line.lstrip()
    if stripped:
      indent = len(line) - len(stripped)
      max_indent = max(max_indent, indent)
  # normalize: assume 2-4 spaces per level
  features.max_nesting_depth = max_indent // 3 if max_indent > 0 else 0

  # risky patterns
  features.has_eval_exec = bool(EVAL_PATTERNS.search(code_text))
  features.has_sql_string = bool(SQL_PATTERNS.search(code_text) or SQL_FSTRING.search(code_text))
  features.has_shell_command = bool(SHELL_PATTERNS.search(code_text))
  features.has_hardcoded_secret = bool(SECRET_PATTERNS.search(code_text))
  features.has_todo_fixme = bool(TODO_PATTERNS.search(code_text))
  features.has_type_cast = bool(CAST_PATTERNS.search(code_text))
  features.has_null_check = bool(NULL_PATTERNS.search(code_text))
  features.has_exception_handling = bool(EXCEPTION_PATTERNS.search(code_text))
  features.has_file_io = bool(FILE_IO_PATTERNS.search(code_text))
  features.has_network_call = bool(NETWORK_PATTERNS.search(code_text))
  features.has_print_debug = bool(PRINT_DEBUG.search(code_text))

  # comment ratio
  comment_lines = sum(1 for line in lines if COMMENT_PATTERNS.match(line))
  features.comment_ratio = comment_lines / max(len(lines), 1)

  # magic numbers
  features.num_magic_numbers = len(MAGIC_NUMBER.findall(code_text))

  # semantic features (computed from chunk content alone)
  defined_names = set(re.findall(r'(?:def|function|func|fn)\s+(\w+)', code_text))
  defined_names |= set(re.findall(r'const\s+(\w+)\s*=', code_text))
  all_calls = set(re.findall(r'\b(\w+)\s*\(', code_text))
  _BUILTINS = {
    'print', 'len', 'range', 'str', 'int', 'float', 'bool', 'list', 'dict',
    'set', 'tuple', 'type', 'isinstance', 'hasattr', 'getattr', 'setattr',
    'super', 'zip', 'map', 'filter', 'sorted', 'enumerate', 'open', 'format',
    'repr', 'id', 'hash', 'min', 'max', 'abs', 'sum', 'any', 'all', 'next',
    'iter', 'vars', 'dir', 'callable', 'staticmethod', 'classmethod', 'property',
  }
  features.cross_function_calls = len(all_calls - defined_names - _BUILTINS)

  import_pat = re.compile(r'^\s*(import\s+\S|from\s+\S+\s+import)', re.MULTILINE)
  features.import_complexity = len(import_pat.findall(code_text))

  try_except_count = len(re.findall(r'\b(try|except|catch)\b', code_text))
  features.error_handling_ratio = round(try_except_count / max(len(lines), 1), 4)

  return features


_BUG_FIX_RE = re.compile(
  r'\b(fix|bug|hotfix|patch|revert|regression|error|crash|issue|broken|wrong|incorrect)\b',
  re.IGNORECASE,
)


def enrich_features(features, pr_file_paths, chunk_file_path, commit_messages):
  """enrich a CodeFeatures object with context that extract_features cannot compute.

  mutates and returns the same features object.

  args:
    features: existing CodeFeatures from extract_features()
    pr_file_paths: list of all file paths changed in this PR
    chunk_file_path: the file this chunk belongs to
    commit_messages: recent commit messages for chunk_file_path from GitHub API
  """
  stem = chunk_file_path.rsplit('/', 1)[-1].rsplit('.', 1)[0]
  features.has_test_coverage = any(
    f'test_{stem}' in p or f'{stem}_test' in p or f'spec_{stem}' in p
    for p in pr_file_paths
  )

  if commit_messages:
    bug_count = sum(1 for msg in commit_messages if _BUG_FIX_RE.search(msg))
    features.commit_history_risk = round(bug_count / len(commit_messages), 4)
  else:
    features.commit_history_risk = 0.0

  return features
