"""Extract the leaf images of the MH-SoyaHealthVision dataset into ml/data/heldout/mh_soyahealthvision/<class>/.

HELD-OUT EVALUATION DATA: never train on it. The destination folder name contains "heldout", which prepare_data.py refuses.

Only the six Soyabean_Leaf_Image_Dataset zips are used; the UAV (drone) zips are a different task and are skipped.
Each inner zip is streamed out of the 10 GB outer zip into a temporary file, its images are unpacked, and the temporary
file is deleted, so the extra disk needed is about the size of the biggest inner zip (1.8 GB).

  python extract_heldout.py "C:/Users/me/Downloads/MH-SoyaHealthVision ... .zip"
"""
import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

# inner zip name -> class folder (the dataset's own labels, in snake_case). Mapping to our 5 categories is in classes.py.
FOLDERS = {
    "Soyabean_Rust.zip": "rust",
    "Caterpillar and Semilooper Pest Attack.zip": "caterpillar_semilooper",
    "Soyabean_Mosaic.zip": "mosaic",
    "Soyabean_Frog_Leaf_Eye.zip": "frog_leaf_eye",
    "Soyabean_Spectoria_Brown_Spot.zip": "septoria_brown_spot",
    "Healthy_Soyabean.zip": "healthy",
}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("outer_zip", type=Path)
    ap.add_argument("--out", type=Path, default=Path("data/heldout/mh_soyahealthvision"))
    a = ap.parse_args()

    outer = zipfile.ZipFile(a.outer_zip)
    members = {Path(i.filename).name: i for i in outer.infolist() if "Soyabean_Leaf_Image_Dataset" in i.filename and i.filename.endswith(".zip")}
    missing = set(FOLDERS) - set(members)
    if missing:
        print("missing inner zips:", sorted(missing))
        return 1

    for inner_name, cls in FOLDERS.items():
        dest = a.out / cls
        if dest.exists() and any(dest.iterdir()):
            print(f"[skip] {cls}: {dest} already has files", flush=True)
            continue
        dest.mkdir(parents=True, exist_ok=True)
        info = members[inner_name]
        print(f"[{cls}] streaming {inner_name} ({info.file_size / 1e9:.2f} GB)…", flush=True)
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            with outer.open(info) as src:
                shutil.copyfileobj(src, tmp, 8 * 1024 * 1024)
            tmp_path = Path(tmp.name)
        n = 0
        try:
            with zipfile.ZipFile(tmp_path) as inner:
                for m in inner.infolist():
                    if m.is_dir() or Path(m.filename).suffix.lower() not in IMAGE_EXT:
                        continue
                    n += 1
                    # flat names with a counter, so two folders inside one zip cannot overwrite each other
                    target = dest / f"{cls}_{n:05d}{Path(m.filename).suffix.lower()}"
                    with inner.open(m) as s, open(target, "wb") as t:
                        shutil.copyfileobj(s, t, 1024 * 1024)
        finally:
            tmp_path.unlink(missing_ok=True)
        print(f"[{cls}] {n} images -> {dest}", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
