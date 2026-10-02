"""Extract verbatim advisory passages from the advisory PDFs into data/advisories/excerpts.json.

Rules this script enforces (CLAUDE.md: no treatment advice without a verified source, never a pesticide dose):
  * Passages are copied WORD FOR WORD from the PDF. Nothing is paraphrased or written by hand.
  * Only descriptive passages (what the condition looks like, when it occurs) are taken. Each passage ends BEFORE any
    control or treatment sentence.
  * A passage is rejected if it contains a dose, a formulation code or a chemical name (the DENY pattern below). The script
    stops with an error instead of writing it.
  * `verified` is always false here. Marking a source verified is a human decision made in data/advisories/sources.json.

Needs poppler's `pdftotext` on PATH.   python scripts/build_advisory_excerpts.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PDFS = ROOT / "data" / "advisories" / "pdfs"
OUT = ROOT / "data" / "advisories" / "excerpts.json"

# Anything that looks like a dose, formulation, spray instruction or a chemical name.
DENY = re.compile(
    r"@|\b\d+(\.\d+)?\s*(ml|mL|g|kg|l|ha|%|ppm)\b|\b(EC|WG|WP|SC|FS|WS|SL)\b|spray|fungicid|insecticid|pesticid|chemical|dose"
    r"|thiamethoxam|imidacloprid|hexaconazole|carbendazim|mancozeb|chlorantraniliprole|tebuconazole|azoxystrobin"
    r"|kresoxim|picoxystrobin|pyraclostrobin|propiconazole|thiram|carboxin|profenofos|quinalphos",
    re.I,
)

SOURCES = {
    "iisr": {
        "file": "ExtensionBulletin2023E_2.pdf",
        "title": "Extension Bulletin 18: Improved Technologies and Recommendations for Maximizing Soybean Productivity (Revised Edition 2023)",
        "publisher": "ICAR-Indian Institute of Soybean Research, Indore",
        "source_url": "http://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf",
    },
}

# (topic, source, passage starts at, passage ends before). Both are literal text found in the PDF.
SPECS = [
    ("rust_like", "iisr", "This is a disease of fungal origin caused by Phakopsora pachyrhizi.", "The control measures are given in Table 9."),
    ("insect_damage", "iisr", "Soybean is infested by a complex of semiloopers.", "Farmers are advised to follow control measures"),
    ("yellow_mosaic", "iisr", "YMD caused by Mungbean Yellow Mosaic India Virus (MYMIV)", "Farmers are advised to carry out seed treatment"),
]


def pages(pdf: Path) -> list[str]:
    """Text of each page: pdftotext separates pages with a form feed."""
    r = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"pdftotext failed on {pdf}")
    return r.stdout.split("")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def main() -> int:
    cache: dict[str, list[str]] = {}
    entries = []
    for topic, key, start, end in SPECS:
        src = SOURCES[key]
        pdf = PDFS / src["file"]
        if key not in cache:
            cache[key] = [norm(t) for t in pages(pdf)]
        text = " ".join(cache[key])
        i = text.find(norm(start))
        if i < 0:
            print(f"[{topic}] start text not found", file=sys.stderr)
            return 1
        j = text.find(norm(end), i)
        if j < 0:
            print(f"[{topic}] end text not found", file=sys.stderr)
            return 1
        passage = norm(text[i:j])
        page = next(n for n, t in enumerate(cache[key], 1) if norm(start)[:60] in t)
        bad = DENY.search(passage)
        if bad:
            print(f"[{topic}] REJECTED: contains {bad.group(0)!r}: {passage[:120]}...", file=sys.stderr)
            return 1
        entries.append({
            "topic": topic, "title": src["title"], "publisher": src["publisher"], "source_url": src["source_url"],
            "published_at": None, "page": page, "excerpt": passage,
            "verified": False,
        })
        print(f"[{topic}] page {page}, {len(passage)} chars OK")
    OUT.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
