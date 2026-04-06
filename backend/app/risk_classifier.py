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


def is_loaded():
  return _model is not None
