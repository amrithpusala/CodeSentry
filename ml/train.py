# train.py — train the bug risk classifier
#
# usage:
#   python ml/train.py --data ml/data/training_data.csv --output ml/model.pt

import argparse
import csv
import time
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split
from model import BugRiskClassifier, count_parameters


class BugDataset(Dataset):
  def __init__(self, csv_path):
    self.features = []
    self.labels = []
    with open(csv_path) as f:
      reader = csv.reader(f)
      next(reader)  # skip header
      for row in reader:
        feats = [float(x) for x in row[:-1]]
        label = float(row[-1])
        self.features.append(feats)
        self.labels.append(label)
    self.features = torch.tensor(self.features, dtype=torch.float32)
    self.labels = torch.tensor(self.labels, dtype=torch.float32).unsqueeze(1)
    print(f'loaded {len(self)} samples from {csv_path}')
    print(f'  buggy: {int(self.labels.sum().item())} ({self.labels.mean().item()*100:.1f}%)')
    print(f'  clean: {len(self) - int(self.labels.sum().item())}')

  def __len__(self):
    return len(self.labels)

  def __getitem__(self, idx):
    return self.features[idx], self.labels[idx]


def train_epoch(model, loader, optimizer, criterion, device):
  model.train()
  total_loss = 0
  correct = 0
  total = 0
  for features, labels in loader:
    features, labels = features.to(device), labels.to(device)
    preds = model(features)
    loss = criterion(preds, labels)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    total_loss += loss.item()
    predicted = (preds > 0.5).float()
    correct += (predicted == labels).sum().item()
    total += labels.size(0)
  return total_loss / len(loader), correct / total


def evaluate(model, loader, criterion, device):
  model.eval()
  total_loss = 0
  correct = 0
  total = 0
  tp = fp = tn = fn = 0
  with torch.no_grad():
    for features, labels in loader:
      features, labels = features.to(device), labels.to(device)
      preds = model(features)
      loss = criterion(preds, labels)
      total_loss += loss.item()
      predicted = (preds > 0.5).float()
      correct += (predicted == labels).sum().item()
      total += labels.size(0)
      tp += ((predicted == 1) & (labels == 1)).sum().item()
      fp += ((predicted == 1) & (labels == 0)).sum().item()
      tn += ((predicted == 0) & (labels == 0)).sum().item()
      fn += ((predicted == 0) & (labels == 1)).sum().item()

  acc = correct / total
  precision = tp / max(tp + fp, 1)
  recall = tp / max(tp + fn, 1)
  f1 = 2 * precision * recall / max(precision + recall, 1e-8)
  return total_loss / len(loader), acc, precision, recall, f1


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--data', type=str, required=True)
  parser.add_argument('--output', type=str, default='ml/model.pt')
  parser.add_argument('--epochs', type=int, default=50)
  parser.add_argument('--batch-size', type=int, default=64)
  parser.add_argument('--lr', type=float, default=0.001)
  parser.add_argument('--patience', type=int, default=10)
  args = parser.parse_args()

  device = torch.device('mps' if torch.backends.mps.is_available()
                         else 'cuda' if torch.cuda.is_available() else 'cpu')
  print(f'device: {device}')

  dataset = BugDataset(args.data)
  train_size = int(0.8 * len(dataset))
  val_size = int(0.1 * len(dataset))
  test_size = len(dataset) - train_size - val_size

  train_set, val_set, test_set = random_split(
    dataset, [train_size, val_size, test_size],
    generator=torch.Generator().manual_seed(42)
  )
  print(f'split: {train_size} train, {val_size} val, {test_size} test')

  train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True)
  val_loader = DataLoader(val_set, batch_size=args.batch_size)
  test_loader = DataLoader(test_set, batch_size=args.batch_size)

  model = BugRiskClassifier().to(device)
  print(f'parameters: {count_parameters(model):,}')

  # use class weights to handle imbalanced data
  num_buggy = int(dataset.labels.sum().item())
  num_clean = len(dataset) - num_buggy
  pos_weight = torch.tensor([num_clean / max(num_buggy, 1)]).to(device)
  criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

  # since we already have sigmoid in the model, use plain BCE
  criterion = nn.BCELoss()

  optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
  scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
    optimizer, T_max=args.epochs, eta_min=1e-6
  )

  best_val_f1 = 0
  no_improve = 0

  print(f'\n{"epoch":>5} {"loss":>8} {"acc":>8} {"val_f1":>8} {"prec":>8} {"rec":>8} {"lr":>10}')
  print('-' * 58)

  for epoch in range(1, args.epochs + 1):
    train_loss, train_acc = train_epoch(model, train_loader, optimizer, criterion, device)
    val_loss, val_acc, precision, recall, f1 = evaluate(model, val_loader, criterion, device)
    lr = optimizer.param_groups[0]['lr']
    scheduler.step()

    print(f'{epoch:5d} {train_loss:8.4f} {train_acc:7.1%} {f1:8.4f} {precision:7.1%} {recall:7.1%} {lr:10.6f}')

    if f1 > best_val_f1:
      best_val_f1 = f1
      no_improve = 0
      torch.save({
        'model_state_dict': model.state_dict(),
        'val_f1': f1,
        'val_precision': precision,
        'val_recall': recall,
        'epoch': epoch,
      }, args.output)
    else:
      no_improve += 1
      if no_improve >= args.patience:
        print(f'\nearly stopping at epoch {epoch}')
        break

  # test set evaluation
  checkpoint = torch.load(args.output, map_location=device, weights_only=True)
  model.load_state_dict(checkpoint['model_state_dict'])
  test_loss, test_acc, test_prec, test_rec, test_f1 = evaluate(
    model, test_loader, criterion, device
  )

  print(f'\ntest results:')
  print(f'  accuracy:  {test_acc:.1%}')
  print(f'  precision: {test_prec:.1%}')
  print(f'  recall:    {test_rec:.1%}')
  print(f'  F1:        {test_f1:.4f}')
  print(f'\nmodel saved to {args.output}')


if __name__ == '__main__':
  main()
