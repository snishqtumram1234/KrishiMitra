"""Run the deployed ONNX model over data/plain_leaf and show what it predicts for the healthy and diseased folders.

Uses evaluate_onnx.preprocess (the backend's preprocessing). Writes artifacts/plain_leaf_predictions.csv.
"""
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np
import onnxruntime as ort

from evaluate_onnx import preprocess

MODEL = Path("../backend/models/soybean_vision.onnx")
CLASSES = json.load(open("../backend/models/soybean_vision.json", encoding="utf-8")).get("classes") or [
    "healthy", "rust_like", "leaf_spot_like", "insect_damage", "unknown"]

sess = ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])
name = sess.get_inputs()[0].name
rows = []
for folder in ("healthy", "diseased"):
    files = sorted(Path("data/plain_leaf", folder).glob("*.jpg"))
    for i in range(0, len(files), 32):
        batch = files[i:i + 32]
        x = np.stack([preprocess(str(p)) for p in batch])
        logits = sess.run(None, {name: x})[0]
        p = np.exp(logits - logits.max(1, keepdims=True))
        p /= p.sum(1, keepdims=True)
        for f, pr in zip(batch, p):
            rows.append({"path": str(f).replace("\\", "/"), "truth": folder, "pred": CLASSES[int(pr.argmax())],
                         "conf": round(float(pr.max()), 3)})

Path("artifacts").mkdir(exist_ok=True)
with open("artifacts/plain_leaf_predictions.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
for folder in ("healthy", "diseased"):
    sub = [r for r in rows if r["truth"] == folder]
    c = Counter(r["pred"] for r in sub)
    print(folder, len(sub), {k: f"{100 * v / len(sub):.0f}%" for k, v in c.most_common()})
