"""Per-class metrics on a split, plus accuracy per orchestrator confidence tier.

  python evaluate.py --ckpt artifacts/best.pt --csv data/splits/test.csv --out artifacts

Also usable for the held-out Indian dataset: point --csv at a CSV of (path,label,source) built
from it. Never train on that data.
"""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader

from train import CsvDataset, build_model, eval_tf, predict

LOW, HIGH = 0.60, 0.85  # keep in sync with backend routing thresholds


def tier_report(probs: np.ndarray, y: np.ndarray) -> dict:
    conf, pred = probs.max(1), probs.argmax(1)
    tiers = {"low (<0.60)": conf < LOW, "mid (0.60-0.85)": (conf >= LOW) & (conf <= HIGH), "high (>0.85)": conf > HIGH}
    out = {}
    for name, mask in tiers.items():
        n = int(mask.sum())
        out[name] = {"n": n, "fraction": round(n / len(y), 4),
                     "accuracy": round(float((pred[mask] == y[mask]).mean()), 4) if n else None}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, default=Path("artifacts/best.pt"))
    ap.add_argument("--csv", type=Path, default=Path("data/splits/test.csv"))
    ap.add_argument("--out", type=Path, default=Path("artifacts"))
    ap.add_argument("--name", default="test")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()

    ck = torch.load(a.ckpt, map_location="cpu")
    classes = ck["classes"]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = build_model(ck["arch"], len(classes), pretrained=False)
    model.load_state_dict(ck["state_dict"])
    model.to(device)

    ds = CsvDataset(a.csv, eval_tf())
    probs, ys = predict(model, DataLoader(ds, 64, num_workers=a.workers), device)
    probs, ys = probs.numpy(), ys.numpy()
    pred = probs.argmax(1)
    labels = list(range(len(classes)))

    report = classification_report(ys, pred, labels=labels, target_names=classes,
                                   output_dict=True, zero_division=0)
    cm = confusion_matrix(ys, pred, labels=labels)
    metrics = {"split": a.name, "n": int(len(ys)), "accuracy": report["accuracy"],
               "macro_f1": report["macro avg"]["f1-score"],
               "per_class": {c: {k: round(report[c][k], 4) for k in ("precision", "recall", "f1-score")}
                             | {"support": int(report[c]["support"])} for c in classes},
               "confidence_tiers": tier_report(probs, ys)}

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"metrics_{a.name}.json").write_text(json.dumps(metrics, indent=2))
    with open(a.out / f"confusion_matrix_{a.name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["true\\pred"] + classes)
        for c, row in zip(classes, cm):
            w.writerow([c] + row.tolist())
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
