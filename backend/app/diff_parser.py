# diff_parser.py — parse unified diffs into reviewable code chunks
#
# when github sends a PR diff, it comes as a unified diff string.
# this module breaks that into structured chunks, each representing
# a changed section of a file. each chunk has:
#   - file path
#   - start/end line numbers
#   - the actual changed code (additions only, since we review new code)
#   - surrounding context lines
#
# chunks are the unit of review: each one gets scored by the risk
# classifier and optionally sent to the LLM for detailed feedback.

import re
from dataclasses import dataclass, field


@dataclass
class DiffChunk:
  file_path: str
  start_line: int
  end_line: int
  added_lines: list[str] = field(default_factory=list)
  context_lines: list[str] = field(default_factory=list)
  raw_patch: str = ''

  @property
  def added_code(self):
    return '\n'.join(self.added_lines)

  @property
  def full_context(self):
    return '\n'.join(self.context_lines)

  @property
  def num_added(self):
    return len(self.added_lines)

  def to_dict(self):
    return {
      'file_path': self.file_path,
      'start_line': self.start_line,
      'end_line': self.end_line,
      'added_lines': self.added_lines,
      'context_lines': self.context_lines,
      'num_added': self.num_added,
    }


# file extensions we actually want to review
REVIEWABLE_EXTENSIONS = {
  '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs',
  '.c', '.cpp', '.h', '.hpp', '.cs', '.rb', '.php', '.swift',
  '.kt', '.scala', '.sql',
}

# files to skip (configs, lockfiles, generated code)
SKIP_PATTERNS = [
  r'package-lock\.json$',
  r'yarn\.lock$',
  r'Pipfile\.lock$',
  r'poetry\.lock$',
  r'\.min\.js$',
  r'\.min\.css$',
  r'\.generated\.',
  r'__pycache__',
  r'node_modules/',
  r'dist/',
  r'build/',
  r'\.d\.ts$',
]


def _should_review(file_path):
  """check if a file is worth reviewing based on extension and path."""
  # skip non-code files
  ext = '.' + file_path.rsplit('.', 1)[-1] if '.' in file_path else ''
  if ext not in REVIEWABLE_EXTENSIONS:
    return False

  # skip generated/vendored files
  for pattern in SKIP_PATTERNS:
    if re.search(pattern, file_path):
      return False

  return True


def parse_diff(diff_text):
  """parse a unified diff string into a list of DiffChunk objects.

  args:
    diff_text: the raw unified diff from github's API

  returns:
    list of DiffChunk, one per changed section of each file
  """
  chunks = []
  current_file = None
  current_chunk = None
  current_line = 0

  for line in diff_text.split('\n'):
    # detect file header
    if line.startswith('diff --git'):
      # save previous chunk
      if current_chunk and current_chunk.num_added > 0:
        chunks.append(current_chunk)
      current_chunk = None

      # extract file path (format: diff --git a/path b/path)
      match = re.search(r'b/(.+)$', line)
      if match:
        current_file = match.group(1)
      continue

    # skip binary files and file mode changes
    if line.startswith('Binary files') or line.startswith('old mode') or line.startswith('new mode'):
      continue

    # detect hunk header: @@ -old_start,old_count +new_start,new_count @@
    hunk_match = re.match(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
    if hunk_match:
      # save previous chunk
      if current_chunk and current_chunk.num_added > 0:
        chunks.append(current_chunk)

      current_line = int(hunk_match.group(1))

      if current_file and _should_review(current_file):
        current_chunk = DiffChunk(
          file_path=current_file,
          start_line=current_line,
          end_line=current_line,
          raw_patch='',
        )
      else:
        current_chunk = None
      continue

    if current_chunk is None:
      continue

    # track the raw patch
    current_chunk.raw_patch += line + '\n'

    if line.startswith('+') and not line.startswith('+++'):
      # added line
      current_chunk.added_lines.append(line[1:])  # strip the +
      current_chunk.end_line = current_line
      current_line += 1
    elif line.startswith('-') and not line.startswith('---'):
      # removed line (don't increment new line counter)
      pass
    else:
      # context line
      if line.startswith(' '):
        current_chunk.context_lines.append(line[1:])
      current_line += 1

  # save last chunk
  if current_chunk and current_chunk.num_added > 0:
    chunks.append(current_chunk)

  return chunks


def merge_small_chunks(chunks, min_lines=3):
  """merge consecutive small chunks in the same file into larger ones.
  this avoids sending tiny 1-2 line changes individually to the classifier.
  """
  if not chunks:
    return []

  merged = [chunks[0]]
  for chunk in chunks[1:]:
    prev = merged[-1]
    # merge if same file and close together
    if (chunk.file_path == prev.file_path and
        chunk.start_line - prev.end_line < 10):
      prev.added_lines.extend(chunk.added_lines)
      prev.context_lines.extend(chunk.context_lines)
      prev.end_line = chunk.end_line
      prev.raw_patch += chunk.raw_patch
    else:
      merged.append(chunk)

  return merged
