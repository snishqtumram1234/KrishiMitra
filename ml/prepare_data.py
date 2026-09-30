"""Map raw dataset folders to the 5 KrishiMitra categories, shrink images, make stratified splits.

Reads   data/raw/<dataset>/<class>/*.jpg     (output of download.py)
Writes  data/processed/<label>/*.jpg         (max side 512, verified RGB JPEGs)
        data/splits/{train,val,test}.csv     (path,label,source)
        data/splits/summary.json

Caveat: ASDID has no plant/session IDs, so near-duplicate photos of the same plant can land in
different splits and inflate test scores. Treat test metrics as optimistic; the held-out Indian
dataset is the honest number.
"""

import argparse
import csv
import json
from pathlib import Path

from PIL import Image
from sklearn.model_selection import train_test_split

from classes import CLASSES, FORBIDDEN_PATH_FRAGMENTS, SOURCE_MAP, source_caps

MAX_SIDE = 512


def check_not_forbidden(path: Path) -> None:
    low = str(path).lower()
    for frag in FORBIDDEN_PATH_FRAGMENTS:
        if frag in low:
            raise SystemExit(f"Refusing {path}: '{frag}' data is held-out evaluation only, never train on it.")


def shrink(src: Path, dst: Path) -> bool:
    """Save a max-side-512 RGB JPEG. Returns False if the image is unreadable."""
    try:
        with Image.open(src) as im:
            im.draft("RGB", (MAX_SIDE * 2, MAX_SIDE * 2))
            im = im.convert("RGB")
            im.thumbnail((MAX_SIDE, MAX_SIDE))
            dst.parent.mkdir(parents=True, exist_ok=True)
            im.save(dst, "JPEG", quality=90)
        return True
    except Exception:  # noqa: BLE001 - corrupt/truncated files are simply dropped
        return False


def collect(raw: Path, processed: Path, images_per_class: int, seed: int) -> list[dict]:
    import random

    rng = random.Random(seed)
    caps = source_caps(images_per_class)
    rows, dropped = [], 0
    for source, label in SOURCE_MAP.items():
        src_dir = raw / source
        if not src_dir.exists():
            print(f"[warn] missing {src_dir}")
            continue
        check_not_forbidden(src_dir)
        files = sorted(p for p in src_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
        for i, f in enumerate(rng.sample(files, min(caps[source], len(files)))):
            dst = processed / label / f"{source.replace('/', '_')}_{i:05d}.jpg"
            if shrink(f, dst):
                rows.append({"path": str(dst.as_posix()), "label": label, "source": source})
            else:
                dropped += 1
    print(f"Collected {len(rows)} images ({dropped} unreadable dropped)")
    return rows


def split(rows: list[dict], seed: int, val: float, test: float) -> dict[str, list[dict]]:
    labels = [r["label"] for r in rows]
    train_val, test_rows = train_test_split(rows, test_size=test, stratify=labels, random_state=seed)
    tv_labels = [r["label"] for r in train_val]
    train_rows, val_rows = train_test_split(
        train_val, test_size=val / (1 - test), stratify=tv_labels, random_state=seed
    )
    return {"train": train_rows, "val": val_rows, "test": test_rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--processed", type=Path, default=Path("data/processed"))
    ap.add_argument("--splits", type=Path, default=Path("data/splits"))
    ap.add_argument("--images-per-class", type=int, default=1500)
    ap.add_argument("--val", type=float, default=0.15)
    ap.add_argument("--test", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    rows = collect(a.raw, a.processed, a.images_per_class, a.seed)
    if not rows:
        raise SystemExit("No images found. Run download.py first.")
    parts = split(rows, a.seed, a.val, a.test)

    a.splits.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, part in parts.items():
        with open(a.splits / f"{name}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["path", "label", "source"])
            w.writeheader()
            w.writerows(part)
        summary[name] = {c: sum(r["label"] == c for r in part) for c in CLASSES}
    (a.splits / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
