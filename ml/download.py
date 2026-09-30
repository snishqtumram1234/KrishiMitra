"""Download ASDID and the Mignoni insect dataset, keeping only a capped random subset per class.

ASDID (Dryad, ~43 GB total) needs a free Dryad API token: create an account at datadryad.org,
open "My account" -> API and set DRYAD_CLIENT_ID / DRYAD_CLIENT_SECRET. Each class zip is
downloaded, sampled, and deleted, so disk use stays small (largest zip is ~8.4 GB, temporarily).
Without credentials, download the zips manually in a browser and pass --asdid-zip-dir.

Mignoni (Mendeley Data) needs no credentials.

Usage:
  python download.py --dest data/raw --images-per-class 1500
"""

import argparse
import hashlib
import os
import random
import re
import zipfile
from pathlib import Path
from typing import Callable

import requests
from tqdm import tqdm

from classes import SOURCE_MAP, mignoni_source, source_caps

DRYAD_DOI = "doi%3A10.5061%2Fdryad.41ns1rnj3"
DRYAD = "https://datadryad.org"
MENDELEY_ZIP = "https://data.mendeley.com/public-api/zip/bycbh73438/download/1"
IMG_RE = re.compile(r"\.(jpe?g|png)$", re.I)
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
MENDELEY_PAGE = "https://data.mendeley.com/datasets/bycbh73438/1"


def stream_to(url: str, out: Path, headers: dict | None = None, sha256: str | None = None) -> None:
    h = hashlib.sha256()
    with requests.get(url, headers={**BROWSER_UA, **(headers or {})}, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(out, "wb") as f, tqdm(total=total, unit="B", unit_scale=True, desc=out.name) as bar:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                h.update(chunk)
                bar.update(len(chunk))
    if sha256 and h.hexdigest() != sha256:
        out.unlink(missing_ok=True)
        raise RuntimeError(f"Checksum mismatch for {out.name}")


def extract_subset(zip_path: Path, dest_root: Path, classify: Callable[[str], str | None],
                   caps: dict[str, int], seed: int) -> dict[str, int]:
    """Extract up to caps[source] random images per source into dest_root/<source>/."""
    rng = random.Random(seed)
    with zipfile.ZipFile(zip_path) as z:
        groups: dict[str, list[str]] = {}
        for name in z.namelist():
            if name.endswith("/") or not IMG_RE.search(name) or "__MACOSX" in name:
                continue
            src = classify(name)
            if src in caps:
                groups.setdefault(src, []).append(name)
        counts = {}
        for src, names in groups.items():
            picked = rng.sample(sorted(names), min(caps[src], len(names)))
            out_dir = dest_root / src
            out_dir.mkdir(parents=True, exist_ok=True)
            for i, name in enumerate(picked):
                (out_dir / f"{i:05d}{Path(name).suffix.lower()}").write_bytes(z.read(name))
            counts[src] = len(picked)
    return counts


def dryad_token() -> str:
    cid, secret = os.environ.get("DRYAD_CLIENT_ID"), os.environ.get("DRYAD_CLIENT_SECRET")
    if not (cid and secret):
        raise SystemExit("Set DRYAD_CLIENT_ID and DRYAD_CLIENT_SECRET, or use --asdid-zip-dir.")
    r = requests.post(f"{DRYAD}/oauth/token", data={
        "grant_type": "client_credentials", "client_id": cid, "client_secret": secret}, timeout=60)
    r.raise_for_status()
    return r.json()["access_token"]


def dryad_files() -> dict[str, dict]:
    v = requests.get(f"{DRYAD}/api/v2/datasets/{DRYAD_DOI}/versions", timeout=60).json()
    versions = v["_embedded"]["stash:versions"]
    files_href = versions[-1]["_links"]["stash:files"]["href"]
    files = requests.get(f"{DRYAD}{files_href}", params={"per_page": 100}, timeout=60).json()
    return {f["path"]: f for f in files["_embedded"]["stash:files"]}


def do_asdid(raw: Path, caps: dict[str, int], seed: int, zip_dir: Path | None, keep_zips: bool) -> None:
    wanted = {src.split("/")[1]: src for src in caps if src.startswith("asdid/")}
    remote = None
    token = None
    for cls, src in wanted.items():
        have = list((raw / src).glob("*")) if (raw / src).exists() else []
        if len(have) >= caps[src]:
            print(f"[skip] {src}: already has {len(have)} images")
            continue
        zip_name = f"{cls}.zip"
        if zip_dir:
            zpath, delete = zip_dir / zip_name, False
        else:
            if remote is None:
                remote, token = dryad_files(), dryad_token()
            info = remote[zip_name]
            print(f"Downloading {zip_name} ({info['size'] / 1e9:.1f} GB)")
            zpath, delete = raw / zip_name, not keep_zips
            stream_to(f"{DRYAD}{info['_links']['stash:download']['href']}", zpath,
                      {"Authorization": f"Bearer {token}"}, info.get("digest"))
        counts = extract_subset(zpath, raw, lambda n, s=src: s, {src: caps[src]}, seed)
        print(f"[ok] {src}: {counts.get(src, 0)} images")
        if delete:
            zpath.unlink()


def do_mignoni(raw: Path, caps: dict[str, int], seed: int, keep_zips: bool, zip_path: Path | None) -> None:
    mine = {s: c for s, c in caps.items() if s.startswith("mignoni/")}
    if all((raw / s).exists() and len(list((raw / s).glob("*"))) >= c for s, c in mine.items()):
        print("[skip] mignoni: already extracted")
        return
    if zip_path:
        zpath, delete = zip_path, False
    else:
        zpath, delete = raw / "mignoni.zip", not keep_zips
        try:
            stream_to(MENDELEY_ZIP, zpath)
        except requests.HTTPError as e:
            zpath.unlink(missing_ok=True)
            raise SystemExit(
                f"Mendeley refused the download ({e}); it blocks some cloud IPs such as Colab.\n"
                f"Download the zip (~860 MB) in your browser from {MENDELEY_PAGE}, upload it, and rerun with\n"
                "  --mignoni-zip /path/to/the.zip"
            )
    counts = extract_subset(zpath, raw, mignoni_source, mine, seed)
    print(f"[ok] mignoni: {counts}")
    if delete:
        zpath.unlink()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", type=Path, default=Path("data/raw"))
    ap.add_argument("--images-per-class", type=int, default=1500,
                    help="image budget per KrishiMitra category, split across its source classes")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--asdid-zip-dir", type=Path, help="folder with manually downloaded ASDID zips")
    ap.add_argument("--mignoni-zip", type=Path, help="manually downloaded Mignoni zip")
    ap.add_argument("--skip-asdid", action="store_true")
    ap.add_argument("--skip-mignoni", action="store_true")
    ap.add_argument("--keep-zips", action="store_true")
    a = ap.parse_args()

    a.dest.mkdir(parents=True, exist_ok=True)
    caps = source_caps(a.images_per_class)
    assert set(caps) == set(SOURCE_MAP)
    if not a.skip_mignoni:
        do_mignoni(a.dest, caps, a.seed, a.keep_zips, a.mignoni_zip)
    if not a.skip_asdid:
        do_asdid(a.dest, caps, a.seed, a.asdid_zip_dir, a.keep_zips)


if __name__ == "__main__":
    main()
