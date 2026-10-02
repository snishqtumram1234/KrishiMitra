"""Split data/plain_leaf/diseased into insect-damage (holes) and leaf-spot candidates, using the plain background.

Leaf = pixels that are clearly coloured (the paper is grey/white). A hole is background-coloured area fully inside the
leaf outline. The healthy folder sets the noise floor, so the threshold is its 99.5th percentile, not a guess.
Also measures dark/brown lesion pixels inside the leaf for the spot candidates.

  python split_diseased_plain.py     # writes artifacts/plain_leaf_features.csv and prints the split
"""
import csv
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def features(path: str) -> dict:
    im = Image.open(path).convert("RGB")
    im.thumbnail((256, 256))
    a = np.asarray(im).astype(np.float32) / 255
    mx, mn = a.max(2), a.min(2)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    leaf = (sat > 0.22) | (mx < 0.35)  # coloured or dark; the paper is bright and grey
    leaf = ndi.binary_opening(leaf, iterations=1)
    lab, n = ndi.label(leaf)
    if n == 0:
        return {"leaf_area": 0, "hole_frac": 0.0, "lesion_frac": 0.0}
    sizes = ndi.sum(leaf, lab, range(1, n + 1))
    leaf = lab == (1 + int(np.argmax(sizes)))  # the biggest blob is the leaf
    filled = ndi.binary_fill_holes(leaf)
    area = float(filled.sum())
    holes = filled & ~leaf
    holes = ndi.binary_opening(holes, iterations=1)  # ignore 1 px pinholes along veins
    # brown/dark lesion pixels: inside the leaf, red >= green (not leaf-green) or very dark
    lesion = leaf & ((r >= g * 0.95) | (mx < 0.18))
    return {"leaf_area": int(area), "hole_frac": float(holes.sum() / max(area, 1)),
            "lesion_frac": float(lesion.sum() / max(area, 1))}


def main() -> None:
    rows = []
    for folder in ("healthy", "diseased"):
        for p in sorted(Path("data/plain_leaf", folder).glob("*.jpg")):
            rows.append({"path": str(p).replace("\\", "/"), "folder": folder, **features(str(p))})
    Path("artifacts").mkdir(exist_ok=True)
    with open("artifacts/plain_leaf_features.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    h = np.array([r["hole_frac"] for r in rows if r["folder"] == "healthy"])
    d = np.array([r["hole_frac"] for r in rows if r["folder"] == "diseased"])
    thr = float(np.percentile(h, 99.5))
    print(f"healthy hole_frac: median {np.median(h):.4f}, p99.5 {thr:.4f}, max {h.max():.4f}")
    print(f"diseased hole_frac: median {np.median(d):.4f}, p25 {np.percentile(d, 25):.4f}, p75 {np.percentile(d, 75):.4f}")
    print(f"diseased above healthy noise floor: {(d > max(thr, 0.002)).sum()} of {len(d)}")
    for folder in ("healthy", "diseased"):
        L = np.array([r["lesion_frac"] for r in rows if r["folder"] == folder])
        print(folder, "lesion_frac median", round(float(np.median(L)), 3), "p90", round(float(np.percentile(L, 90)), 3))


if __name__ == "__main__":
    main()
