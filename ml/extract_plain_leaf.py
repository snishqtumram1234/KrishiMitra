"""Shrink the "Soybean Healthy and Diseased Images Dataset" zip (single leaf on a plain background, 2 labels) for training.

Reads the zip directly (nothing is unpacked in full) and writes 512 px copies:
  data/plain_leaf/healthy/*.jpg
  data/plain_leaf/diseased/*.jpg      (not yet split into insect damage / leaf spot)

  python extract_plain_leaf.py --zip "C:/Users/<you>/Downloads/Soybean Healthy and Diseased Images Dataset.zip"
"""
import argparse
import io
import re
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = None  # the originals are up to 108 MP phone photos from a trusted dataset
LONG = 512
_zip: zipfile.ZipFile | None = None


def shrink(job):
    global _zip
    zip_path, name, dst = job
    if _zip is None:
        _zip = zipfile.ZipFile(zip_path)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(_zip.read(name))) as im:
        im.draft("RGB", (LONG * 2, LONG * 2))  # JPEG decodes at a smaller scale: much faster for huge photos
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((LONG, LONG), Image.BILINEAR)
        im.save(dst, quality=92)
    return str(dst)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("data/plain_leaf"))
    a = ap.parse_args()

    jobs = []
    with zipfile.ZipFile(a.zip) as z:
        for info in z.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".jpg"):
                continue
            # the top folder is also called "...Healthy and Diseased...", so look only at the class folder
            label = "diseased" if "Soybean Diseased/" in info.filename else "healthy"
            num = re.search(r"\((\d+)\)", info.filename)
            jobs.append((str(a.zip), info.filename, str(a.out / label / f"{label}_{int(num.group(1)):04d}.jpg")))
    with ProcessPoolExecutor() as pool:
        done = list(pool.map(shrink, jobs, chunksize=4))
    print(f"wrote {len(done)} images under {a.out}")


if __name__ == "__main__":
    main()
