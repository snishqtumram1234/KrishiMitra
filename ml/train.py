"""Fine-tune MobileNetV3-Large or EfficientNet-B0 on the prepared splits.

  python train.py --arch mobilenet_v3_large --epochs 12 --out artifacts
Keeps the checkpoint with the best validation macro-F1.
"""

import argparse
import csv
import json
from pathlib import Path

import torch
from PIL import Image
from sklearn.metrics import f1_score
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms as T

from classes import CLASSES

MEAN, STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)
SIZE = 224


def build_model(arch: str, num_classes: int, pretrained: bool) -> nn.Module:
    if arch == "mobilenet_v3_large":
        w = models.MobileNet_V3_Large_Weights.IMAGENET1K_V2 if pretrained else None
        m = models.mobilenet_v3_large(weights=w)
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, num_classes)
    elif arch == "efficientnet_b0":
        w = models.EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
        m = models.efficientnet_b0(weights=w)
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, num_classes)
    else:
        raise ValueError(f"unknown arch {arch}")
    return m


def train_tf() -> T.Compose:
    return T.Compose([
        T.RandomResizedCrop(SIZE, scale=(0.6, 1.0)),
        T.RandomHorizontalFlip(),
        T.RandomVerticalFlip(),
        T.ColorJitter(0.3, 0.3, 0.2, 0.02),
        T.ToTensor(),
        T.Normalize(MEAN, STD),
    ])


def eval_tf() -> T.Compose:
    return T.Compose([T.Resize(256), T.CenterCrop(SIZE), T.ToTensor(), T.Normalize(MEAN, STD)])


class CsvDataset(Dataset):
    def __init__(self, csv_path: Path, tf):
        with open(csv_path, newline="") as f:
            self.rows = list(csv.DictReader(f))
        self.tf = tf
        self.idx = {c: i for i, c in enumerate(CLASSES)}

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i: int):
        r = self.rows[i]
        with Image.open(r["path"]) as im:
            return self.tf(im.convert("RGB")), self.idx[r["label"]]


@torch.no_grad()
def predict(model: nn.Module, loader: DataLoader, device: str):
    model.eval()
    probs, ys = [], []
    for x, y in loader:
        probs.append(torch.softmax(model(x.to(device)), dim=1).cpu())
        ys.append(y)
    return torch.cat(probs), torch.cat(ys)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=Path, default=Path("data/splits"))
    ap.add_argument("--out", type=Path, default=Path("artifacts"))
    ap.add_argument("--arch", default="mobilenet_v3_large", choices=["mobilenet_v3_large", "efficientnet_b0"])
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--no-pretrained", action="store_true", help="for smoke tests only")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    torch.manual_seed(a.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    a.out.mkdir(parents=True, exist_ok=True)

    train_dl = DataLoader(CsvDataset(a.splits / "train.csv", train_tf()), a.batch_size, shuffle=True,
                          num_workers=a.workers, drop_last=True)
    val_dl = DataLoader(CsvDataset(a.splits / "val.csv", eval_tf()), a.batch_size, num_workers=a.workers)

    model = build_model(a.arch, len(CLASSES), not a.no_pretrained).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=a.epochs)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.1)
    scaler = torch.amp.GradScaler(enabled=device == "cuda")

    best, history = -1.0, []
    for epoch in range(1, a.epochs + 1):
        model.train()
        total = 0.0
        for x, y in train_dl:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            with torch.autocast(device_type=device, enabled=device == "cuda"):
                loss = loss_fn(model(x), y)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            total += loss.item() * len(x)
        sched.step()

        probs, ys = predict(model, val_dl, device)
        f1 = f1_score(ys, probs.argmax(1), average="macro")
        acc = (probs.argmax(1) == ys).float().mean().item()
        history.append({"epoch": epoch, "train_loss": total / (len(train_dl) * a.batch_size),
                        "val_macro_f1": f1, "val_acc": acc})
        print(history[-1])
        if f1 > best:
            best = f1
            torch.save({"arch": a.arch, "classes": CLASSES, "state_dict": model.state_dict()},
                       a.out / "best.pt")

    (a.out / "train_history.json").write_text(json.dumps(history, indent=2))
    print(f"Best val macro-F1: {best:.4f} -> {a.out / 'best.pt'}")


if __name__ == "__main__":
    main()
