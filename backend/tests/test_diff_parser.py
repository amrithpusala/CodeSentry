# test_diff_parser.py — verify diff parsing works correctly

from app.diff_parser import parse_diff, merge_small_chunks, _should_review


# --- file filtering ---

def test_should_review_python():
  assert _should_review('app/main.py') is True

def test_should_review_javascript():
  assert _should_review('src/App.jsx') is True

def test_should_review_typescript():
  assert _should_review('lib/utils.ts') is True

def test_skip_lockfile():
  assert _should_review('package-lock.json') is False

def test_skip_minified():
  assert _should_review('dist/bundle.min.js') is False

def test_skip_config():
  assert _should_review('tsconfig.json') is False

def test_skip_markdown():
  assert _should_review('README.md') is False


# --- diff parsing ---

SAMPLE_DIFF = """diff --git a/app/main.py b/app/main.py
index abc1234..def5678 100644
--- a/app/main.py
+++ b/app/main.py
@@ -10,6 +10,8 @@ def hello():
     return "hello"
 
 def process_data(data):
+    if data is None:
+        return []
     result = []
     for item in data:
         result.append(item * 2)
@@ -25,3 +27,5 @@ def cleanup():
     pass
+
+def new_function():
+    return 42
"""

def test_parse_diff_basic():
  chunks = parse_diff(SAMPLE_DIFF)
  assert len(chunks) == 2
  assert chunks[0].file_path == 'app/main.py'

def test_parse_diff_added_lines():
  chunks = parse_diff(SAMPLE_DIFF)
  # first chunk has the None check (with original indentation)
  assert any('if data is None:' in line for line in chunks[0].added_lines)
  assert any('return []' in line for line in chunks[0].added_lines)

def test_parse_diff_line_numbers():
  chunks = parse_diff(SAMPLE_DIFF)
  assert chunks[0].start_line == 10

def test_parse_diff_second_chunk():
  chunks = parse_diff(SAMPLE_DIFF)
  # second chunk is the new_function
  assert any('def new_function():' in line for line in chunks[1].added_lines)
  assert any('return 42' in line for line in chunks[1].added_lines)

def test_parse_diff_skips_non_code():
  diff = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1,3 +1,4 @@
 # Hello
+New line
"""
  chunks = parse_diff(diff)
  assert len(chunks) == 0  # markdown should be skipped

def test_parse_diff_multiple_files():
  diff = """diff --git a/app/main.py b/app/main.py
--- a/app/main.py
+++ b/app/main.py
@@ -1,3 +1,4 @@
 import os
+import sys
 
diff --git a/app/utils.py b/app/utils.py
--- a/app/utils.py
+++ b/app/utils.py
@@ -5,3 +5,5 @@
 def helper():
+    x = 1
+    return x
"""
  chunks = parse_diff(diff)
  assert len(chunks) == 2
  assert chunks[0].file_path == 'app/main.py'
  assert chunks[1].file_path == 'app/utils.py'


# --- chunk merging ---

def test_merge_small_chunks():
  chunks = parse_diff(SAMPLE_DIFF)
  # both chunks are in the same file and close together
  merged = merge_small_chunks(chunks)
  assert len(merged) <= len(chunks)


# --- chunk to_dict ---

def test_chunk_to_dict():
  chunks = parse_diff(SAMPLE_DIFF)
  d = chunks[0].to_dict()
  assert 'file_path' in d
  assert 'added_lines' in d
  assert 'start_line' in d
  assert 'num_added' in d
