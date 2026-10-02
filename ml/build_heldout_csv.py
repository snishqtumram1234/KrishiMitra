"""Build the held-out evaluation CSV (path,label,source) from the extracted MH-SoyaHealthVision leaf images.

HELD-OUT EVALUATION DATA: this CSV is for evaluate_onnx.py only. Never feed it to train.py or prepare_data.py.
The mapping below lives here, NOT in classes.py, because classes.py is the training taxonomy and must never mention
held-out data.

  python build_heldout_csv.py            # writes data/heldout/mh_soyahealthvision.csv
"""
import argparse
import csv
from pathlib import Path

# dataset folder -> KrishiMitra category (confirmed: Mosaic is a virus disease outside our categories, so `unknown`,
# the same way bacterial blight / downy mildew / potassium deficiency are `unknown` in training).
MAPPING = {
    "rust": "rust_like",
    "frog_leaf_eye": "leaf_spot_like",
    "septoria_brown_spot": "leaf_spot_like",
    "caterpillar_semilooper": "insect_damage",
    "mosaic": "unknown",
    "healthy": "healthy",
}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("data/heldout/mh_soyahealthvision"))
    ap.add_argument("--out", type=Path, default=Path("data/heldout/mh_soyahealthvision.csv"))
    a = ap.parse_args()

    rows = []
    for folder, label in MAPPING.items():
        files = sorted(p for p in (a.root / folder).glob("*") if p.suffix.lower() in IMAGE_EXT)
        if not files:
            raise SystemExit(f"no images in {a.root / folder}")
        rows += [{"path": str(p).replace("\\", "/"), "label": label, "source": f"mh_soyahealthvision/{folder}"} for p in files]

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "label", "source"])
        w.writeheader()
        w.writerows(rows)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["label"]] = counts.get(r["label"], 0) + 1
    print(f"{len(rows)} images -> {a.out}\n{counts}")


if __name__ == "__main__":
    main()
