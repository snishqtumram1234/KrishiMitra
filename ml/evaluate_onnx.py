"""Evaluate the DEPLOYED ONNX model (backend/models/soybean_vision.onnx) on a CSV of (path,label,source).

It uses the same preprocessing as the backend (backend/app/services/vision_service.py: EXIF transpose, RGB, resize the
short side to 256 with bilinear, centre-crop 224, scale to [0,1]), so the numbers describe what farmers actually get.

  python evaluate_onnx.py --csv data/heldout/mh_soyahealthvision.csv --name heldout

Writes artifacts/metrics_<name>.json, confusion_matrix_<name>.csv and predictions_<name>.csv (one row per image, for
threshold tuning). Per-source recall shows which original dataset folder (for example mosaic) the model gets wrong.
"""
import argparse
import csv
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps
from sklearn.metrics import classification_report, confusion_matrix

LOW, HIGH = 0.60, 0.85  # keep in sync with backend routing thresholds
RESIZE, CROP = 256, 224  # must match backend vision_service.py and ml/train.py eval_tf


def preprocess(path: str) -> np.ndarray:
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        w, h = im.size
        size = (RESIZE, int(RESIZE * h / w)) if w <= h else (int(RESIZE * w / h), RESIZE)
        im = im.resize(size, Image.BILINEAR)
        w, h = im.size
        left, top = int(round((w - CROP) / 2.0)), int(round((h - CROP) / 2.0))
        im = im.crop((left, top, left + CROP, top + CROP))
        arr = np.asarray(im, dtype=np.float32) / 255.0
    return arr.transpose(2, 0, 1)


def tiers(conf: np.ndarray, correct: np.ndarray) -> dict:
    masks = {"low (<0.60)": conf < LOW, "mid (0.60-0.85)": (conf >= LOW) & (conf <= HIGH), "high (>0.85)": conf > HIGH}
    out = {}
    for name, m in masks.items():
        n = int(m.sum())
        out[name] = {"n": n, "fraction": round(n / len(conf), 4), "accuracy": round(float(correct[m].mean()), 4) if n else None}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, default=Path("../backend/models/soybean_vision.onnx"))
    ap.add_argument("--meta", type=Path, default=Path("../backend/models/soybean_vision.json"))
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("artifacts"))
    ap.add_argument("--name", default="heldout")
    ap.add_argument("--batch", type=int, default=32)
    a = ap.parse_args()

    classes = json.loads(a.meta.read_text())["classes"]
    index = {c: i for i, c in enumerate(classes)}
    rows = list(csv.DictReader(open(a.csv, encoding="utf-8")))
    sess = ort.InferenceSession(str(a.model), providers=["CPUExecutionProvider"])
    name = sess.get_inputs()[0].name

    probs = []
    # Decoding the full-resolution photos is the slow part, so it runs on every core. The pixels are identical.
    with ProcessPoolExecutor() as pool:
        for i in range(0, len(rows), a.batch):
            batch = np.stack(list(pool.map(preprocess, [r["path"] for r in rows[i:i + a.batch]], chunksize=2)))
            probs.append(sess.run(None, {name: batch})[0])
            print(f"\r{min(i + a.batch, len(rows))}/{len(rows)}", end="", flush=True)
    print()
    probs = np.concatenate(probs)
    y = np.array([index[r["label"]] for r in rows])
    pred = probs.argmax(1)
    conf = probs.max(1)
    correct = pred == y
    labels = list(range(len(classes)))

    rep = classification_report(y, pred, labels=labels, target_names=classes, output_dict=True, zero_division=0)
    cm = confusion_matrix(y, pred, labels=labels)
    sources = sorted({r["source"] for r in rows})
    by_source = {}
    for s in sources:
        m = np.array([r["source"] == s for r in rows])
        counts = np.bincount(pred[m], minlength=len(classes))
        by_source[s] = {"n": int(m.sum()), "recall": round(float(correct[m].mean()), 4),
                        "predicted_as": {c: int(n) for c, n in zip(classes, counts) if n}}
    metrics = {
        "split": a.name, "n": int(len(y)), "accuracy": round(float(correct.mean()), 4), "macro_f1": round(rep["macro avg"]["f1-score"], 4),
        "per_class": {c: {k: round(rep[c][k], 4) for k in ("precision", "recall", "f1-score")} | {"support": int(rep[c]["support"])} for c in classes},
        "confidence_tiers": tiers(conf, correct),
        "by_source": by_source,
    }
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"metrics_{a.name}.json").write_text(json.dumps(metrics, indent=2))
    with open(a.out / f"confusion_matrix_{a.name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["true\\pred"] + classes)
        for c, row in zip(classes, cm):
            w.writerow([c] + row.tolist())
    with open(a.out / f"predictions_{a.name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "source", "label", "pred", "confidence"] + [f"p_{c}" for c in classes])
        for k, r in enumerate(rows):
            w.writerow([r["path"], r["source"], r["label"], classes[pred[k]], round(float(conf[k]), 4)] + [round(float(x), 4) for x in probs[k]])
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
