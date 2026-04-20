# risk_classifier.py — score code chunks using the trained bug risk model

import os
import sys
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ml'))
from model import BugRiskClassifier
from app.feature_extractor import extract_features

_model = None
_device = torch.device('cpu')
THRESHOLD = 0.6


def load_model(model_path=None):
  global _model
  if model_path is None:
    model_path = os.path.join(
      os.path.dirname(__file__), '..', '..', 'ml', 'model.pt'
    )
  if not os.path.exists(model_path):
    print(f'risk classifier not found at {model_path} (all chunks will go to LLM)')
    return False
  try:
    checkpoint = torch.load(model_path, map_location=_device, weights_only=True)
    _model = BugRiskClassifier().to(_device)
    _model.load_state_dict(checkpoint['model_state_dict'])
    _model.eval()
    print(f'loaded risk classifier (F1: {checkpoint.get("val_f1", 0):.4f})')
    return True
  except Exception as e:
    print(f'failed to load risk classifier: {e}')
    return False


def score_chunks(chunks):
  """score a list of DiffChunks. returns list of (chunk, score, label)."""
  if not chunks:
    return []
  if _model is None:
    return [(c, 0.7, 'medium') for c in chunks]

  vectors = [extract_features(c).to_vector() for c in chunks]
  tensor = torch.tensor(vectors, dtype=torch.float32).to(_device)

  with torch.no_grad():
    scores = _model(tensor).squeeze(-1).tolist()
  if isinstance(scores, float):
    scores = [scores]

  results = []
  for chunk, score in zip(chunks, scores):
    label = 'high' if score >= 0.7 else 'medium' if score >= THRESHOLD else 'low'
    results.append((chunk, round(score, 4), label))
  return results


def score_chunks_with_context(chunks, enriched_features):
  """score chunks using the PyTorch model, then apply semantic adjustments.

  args:
    chunks: list of DiffChunk
    enriched_features: dict mapping id(chunk) -> CodeFeatures with new fields populated

  returns:
    list of (chunk, score, label) — same shape as score_chunks()
  """
  base_results = score_chunks(chunks)
  adjusted = []
  for chunk, base_score, _ in base_results:
    score = base_score
    feat = enriched_features.get(id(chunk))
    if feat is not None:
      if feat.commit_history_risk > 0.5:
        score = min(score + 0.10, 1.0)
      if not feat.has_test_coverage and feat.cross_function_calls > 5:
        score = min(score + 0.05, 1.0)
      if feat.import_complexity > 5:
        score = min(score + 0.05, 1.0)
      if feat.error_handling_ratio < 0.05 and feat.cross_function_calls > 3:
        score = min(score + 0.05, 1.0)
    score = round(score, 4)
    label = 'high' if score >= 0.7 else 'medium' if score >= THRESHOLD else 'low'
    adjusted.append((chunk, score, label))
  return adjusted


def get_focus_areas(features):
  """return list of focus-area strings for the LLM prompt based on classifier signals."""
  areas = []
  if features.has_eval_exec:
    areas.append('code execution via eval/exec (injection risk)')
  if features.has_sql_string:
    areas.append('SQL string construction (injection risk)')
  if features.has_hardcoded_secret:
    areas.append('potential hardcoded credential')
  if features.has_shell_command:
    areas.append('shell command execution')
  if features.cyclomatic_estimate > 8:
    areas.append(f'high cyclomatic complexity ({features.cyclomatic_estimate})')
  if features.commit_history_risk > 0.4:
    areas.append(f'file has {features.commit_history_risk:.0%} bug-fix commit history')
  if not features.has_test_coverage:
    areas.append('no corresponding test file in this PR')
  if features.cross_function_calls > 8:
    areas.append(f'calls {features.cross_function_calls} external functions (integration risk)')
  if features.error_handling_ratio < 0.05 and features.num_added_lines > 20:
    areas.append('low error handling coverage for a large change')
  return areas


def is_loaded():
  return _model is not None
