# model.py — bug risk classifier architecture

import torch
import torch.nn as nn


class BugRiskClassifier(nn.Module):
  def __init__(self, input_dim=27, hidden_dim=128, dropout=0.2):
    super().__init__()
    self.net = nn.Sequential(
      nn.Linear(input_dim, hidden_dim),
      nn.BatchNorm1d(hidden_dim),
      nn.ReLU(),
      nn.Dropout(dropout),

      nn.Linear(hidden_dim, hidden_dim),
      nn.BatchNorm1d(hidden_dim),
      nn.ReLU(),
      nn.Dropout(dropout),

      nn.Linear(hidden_dim, 64),
      nn.BatchNorm1d(64),
      nn.ReLU(),
      nn.Dropout(dropout),

      nn.Linear(64, 1),
      nn.Sigmoid(),
    )

  def forward(self, x):
    return self.net(x)


def count_parameters(model):
  return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == '__main__':
  model = BugRiskClassifier()
  print(f'parameters: {count_parameters(model):,}')
  print(model)
  dummy = torch.randn(8, 27)
  out = model(dummy)
  print(f'input: {dummy.shape}, output: {out.shape}')
  print(f'range: [{out.min().item():.4f}, {out.max().item():.4f}]')
