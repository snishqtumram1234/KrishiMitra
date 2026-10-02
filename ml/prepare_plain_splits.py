"""Combine the field splits with the plain-background leaves (data/plain_leaf) into data/splits_field_plain/*.csv.

Used from the plain-leaf photos:
  - diseased leaves with holes (hole_frac above the healthy noise floor) -> insect_damage
  - a seeded sample of the healthy leaves                                -> healthy
Left out on purpose: the diseased leaves without holes. The dataset only says "Diseased"; most of those look almost
normal, so any label we gave them would be a guess.

Each class is split by photo number in contiguous blocks (70% train, 10% val, 20% test), like prepare_field.py, so
neighbouring shots stay together. Also writes test_plain.csv (only the plain-leaf test photos) for a separate score.

  python prepare_plain_splits.py
"""
import csv
import random
from pathlib import Path

HOLE_MIN = 0.002  # healthy leaves score at most 0.0004 at the 99.5th percentile (see split_diseased_plain.py)
HEALTHY_USED = 400
OUT = Path("data/splits_field_plain")


def main() -> None:
    feats = list(csv.DictReader(open("artifacts/plain_leaf_features.csv", encoding="utf-8")))
    holes = sorted(r["path"] for r in feats if r["folder"] == "diseased" and float(r["hole_frac"]) > HOLE_MIN)
    healthy = sorted(r["path"] for r in feats if r["folder"] == "healthy")
    random.Random(7).shuffle(healthy)
    healthy = sorted(healthy[:HEALTHY_USED])

    plain: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    for paths, label in ((holes, "insect_damage"), (healthy, "healthy")):
        n = len(paths)
        for i, p in enumerate(paths):
            split = "train" if i < int(n * 0.7) else "val" if i < int(n * 0.8) else "test"
            plain[split].append({"path": p, "label": label, "source": f"plain_leaf/{label}"})

    OUT.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val", "test"):
        base = list(csv.DictReader(open(f"data/splits_field/{split}.csv", encoding="utf-8")))
        rows = base + plain[split]
        with open(OUT / f"{split}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["path", "label", "source"])
            w.writeheader()
            w.writerows(rows)
        counts: dict[str, int] = {}
        for r in rows:
            counts[r["label"]] = counts.get(r["label"], 0) + 1
        print(split, len(rows), counts, "| plain added:", len(plain[split]))
    with open(OUT / "test_plain.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "label", "source"])
        w.writeheader()
        w.writerows(plain["test"])


if __name__ == "__main__":
    main()
