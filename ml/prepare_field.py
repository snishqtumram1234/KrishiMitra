"""Prepare the Maharashtra field photos (MH-SoyaHealthVision leaves) for TRAINING the demo model.

This deliberately uses the dataset that was previously held-out. To keep an honest test, every original folder is split
by capture order (file order): the first 70% train, the next 10% validation, the last 20% test. Neighbouring shots of
the same plant stay in the same split, which is fairer than a random split, but the test number is STILL optimistic:
there is no independent field. Report it as "tested on a held-back part of the same dataset".

Photos are shrunk once (long side 512) so training is not dominated by decoding 3000 px JPEGs.

  python prepare_field.py            # writes data/field/{train,val,test}/<label>/*.jpg and data/splits_field/*.csv
"""
import argparse
import csv
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps

LONG = 512


def shrink(job):
    src, dst = job
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((LONG, LONG), Image.BILINEAR)
        im.save(dst, quality=92)
    return str(dst).replace("\\", "/")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=Path("data/heldout/mh_soyahealthvision.csv"))
    ap.add_argument("--out", type=Path, default=Path("data/field"))
    ap.add_argument("--splits", type=Path, default=Path("data/splits_field"))
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.csv, encoding="utf-8")))
    by_source: dict[str, list[dict]] = {}
    for r in rows:
        by_source.setdefault(r["source"], []).append(r)

    jobs, meta = [], []
    for source, items in by_source.items():
        items = sorted(items, key=lambda r: r["path"])  # file names carry the capture order
        n = len(items)
        a1, a2 = int(n * 0.7), int(n * 0.8)
        for i, r in enumerate(items):
            split = "train" if i < a1 else "val" if i < a2 else "test"
            dst = a.out / split / r["label"] / (Path(r["source"]).name + "_" + Path(r["path"]).stem + ".jpg")
            jobs.append((r["path"], dst))
            meta.append({"label": r["label"], "source": source, "split": split})

    with ProcessPoolExecutor() as pool:
        paths = list(pool.map(shrink, jobs, chunksize=4))
    a.splits.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val", "test"):
        with open(a.splits / f"{split}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["path", "label", "source"])
            w.writeheader()
            for p, m in zip(paths, meta):
                if m["split"] == split:
                    w.writerow({"path": p, "label": m["label"], "source": m["source"]})
    for split in ("train", "val", "test"):
        c: dict[str, int] = {}
        for m in meta:
            if m["split"] == split:
                c[m["label"]] = c.get(m["label"], 0) + 1
        print(split, sum(c.values()), c)


if __name__ == "__main__":
    main()
