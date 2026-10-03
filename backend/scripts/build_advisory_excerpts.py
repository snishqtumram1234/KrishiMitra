"""Extract verbatim advisory passages from the advisory PDFs into data/advisories/excerpts.json.

Rules this script enforces (CLAUDE.md: no treatment advice without a verified source, never a pesticide dose):
  * Passages are copied WORD FOR WORD from the PDF. Nothing is paraphrased or written by hand.
  * Only descriptive passages (what the condition looks like, when it occurs) are taken. Each passage ends BEFORE any
    control or treatment sentence.
  * A passage is rejected if it contains a dose, a formulation code or a chemical name (the DENY pattern below). The script
    stops with an error instead of writing it.
  * `verified` is always false here. Marking a source verified is a human decision made in data/advisories/sources.json.

Needs poppler's `pdftotext` on PATH, and PyMuPDF for the IPM package (see shifted_pages).
  python scripts/build_advisory_excerpts.py
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
    "ipm": {
        "file": "SoyabeanBulletin.pdf",
        "title": "Integrated Pest Management Package for Soybean (2014)",
        "publisher": "NCIPM (ICAR) and Directorate of Plant Protection, Quarantine & Storage, Govt. of India",
        "source_url": "https://niphm.gov.in/IPMPackages/Soyabean.pdf",
        "reader": "shifted",
    },
}

# (topic, kind, source, passage starts at, passage ends before, search only after this text). Texts are literal PDF text.
# kind "description": what the condition looks like. kind "management": non-chemical good practices only; the passage ends
# BEFORE the first item that names a product or dose, and DENY rejects it if anything slipped through.
SPECS = [
    ("rust_like", "description", "iisr", "This is a disease of fungal origin caused by Phakopsora pachyrhizi.", "The control measures are given in Table 9.", None),
    ("rust_like", "management", "iisr", "1.Soybean cultivation during rabi and summer", "3.Basal application of Zinc", "Disease management in soybean"),
    ("insect_damage", "description", "iisr", "Soybean is infested by a complex of semiloopers.", "Farmers are advised to follow control measures", None),
    ("insect_damage", "management", "iisr", "1.Use recommended seed rate.", "5.Spray of biological insecticides", "Soybean is infested by a complex of semiloopers."),
    ("yellow_mosaic", "description", "iisr", "YMD caused by Mungbean Yellow Mosaic India Virus (MYMIV)", "Farmers are advised to carry out seed treatment", None),
    # IPM package: leaf spot (monitoring, cultural practices) and healthy crops (routine monitoring). No chemical passages.
    ("leaf_spot_like", "management", "ipm", "Observe five leaves from each plant", "For viral diseases", "For leaf spot and blight diseases"),
    ("leaf_spot_like", "management", "ipm", "Cleaning of infected stubbles", "Inter-cropping soybean", "3.2. Cultural practices"),
    ("healthy", "management", "ipm", "Surveillance on disease incidence and severity", "For root rot and crown rot diseases", "Disease monitoring"),
    ("healthy", "management", "ipm", "Field scouting should be undertaken", "b. Pest monitoring", "2. Field scouting"),
]

# Table rows, copied cell by cell (each cell must appear on that page) and labelled with the table's own column headers.
# Only columns whose reading order is unambiguous in the PDF are used.
TABLE_ROWS = [
    ("leaf_spot_like", "description", "ipm", "2.3. Major Diseases of National and Regional Importance",
     [("Disease", "Myrothecium leaf spot"), ("Pathogen", "Myrothecium roridum Tode"), ("Scouting", "Flowering to pod filling stage"),
      ("States", "M.P., Rajasthan, Karnataka, A.P., Maharashtra and Uttarakhand")]),
    ("leaf_spot_like", "description", "ipm", "2.3. Major Diseases of National and Regional Importance",
     [("Disease", "Frog eye leaf spot"), ("Pathogen", "Cercospora sojina K.Hara"), ("Scouting", "Flowering to seed set")]),
    ("leaf_spot_like", "management", "ipm", "Disease resistant/ tolerant varieties",
     [("Resistant/tolerant varieties for Frog eye leaf spot", "Bragg, JS 80-21, KHSb 2 and VLS 21"),
      ("Resistant/tolerant varieties for Myrothecium leaf spot", "JS 71-05, JS 335, MACS 13, MACS 124, MAUS 47 and NRC 7")]),
]


def pages(pdf: Path) -> list[str]:
    """Text of each page: pdftotext separates pages with a form feed."""
    r = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"pdftotext failed on {pdf}")
    return r.stdout.split("")


def _unshift(text: str) -> str:
    """This PDF's TimesNewRoman subset stores some text 29 code points low (space is 0x03, "P" is "3") with a ligature
    glyph for "fi"; PDF readers show it scrambled. Shift a run back only if it is clearly shifted: it holds an encoded
    space, or it has no lowercase letters but decodes to lowercase words. Plain runs are left exactly as they are."""
    decoded = "".join("fi" if c == "¿" else chr(ord(c) + 29) if ord(c) + 29 < 0x7F else c for c in text)
    if any(ord(c) < 0x20 for c in text):
        return decoded
    letters = [c for c in decoded if c.isalpha()]
    if (not any(c.islower() for c in text) and re.search(r"[A-Z0-9]{3}", text) and letters
            and sum(c.islower() for c in letters) > 0.6 * len(letters)):
        return decoded
    return text


def shifted_pages(pdf: Path) -> list[str]:
    import fitz  # PyMuPDF keeps the encoded spaces that pdftotext drops

    out = []
    for page in fitz.open(pdf):
        lines = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                lines.append("".join(_unshift(span["text"]) for span in line["spans"]))
        out.append("\n".join(lines))
    return out


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def main() -> int:
    cache: dict[str, list[str]] = {}
    entries = []
    for topic, kind, key, start, end, after in SPECS:
        src = SOURCES[key]
        pdf = PDFS / src["file"]
        if key not in cache:
            reader = shifted_pages if src.get("reader") == "shifted" else pages
            cache[key] = [norm(t) for t in reader(pdf)]
        text = " ".join(cache[key])
        base = text.find(norm(after)) if after else 0
        if base < 0:
            print(f"[{topic}/{kind}] anchor text not found", file=sys.stderr)
            return 1
        i = text.find(norm(start), base)
        if i < 0:
            print(f"[{topic}/{kind}] start text not found", file=sys.stderr)
            return 1
        j = text.find(norm(end), i)
        if j < 0:
            print(f"[{topic}/{kind}] end text not found", file=sys.stderr)
            return 1
        passage = norm(text[i:j])
        page = next(n for n, t in enumerate(cache[key], 1) if norm(start)[:40] in t)
        bad = DENY.search(passage)
        if bad:
            print(f"[{topic}/{kind}] REJECTED: contains {bad.group(0)!r}: {passage[:120]}...", file=sys.stderr)
            return 1
        entries.append({
            "topic": topic, "kind": kind, "title": src["title"], "publisher": src["publisher"], "source_url": src["source_url"],
            "published_at": None, "page": page, "excerpt": passage,
            "verified": False,
        })
        print(f"[{topic}/{kind}] page {page}, {len(passage)} chars OK: {passage}")
    for topic, kind, key, anchor, cells in TABLE_ROWS:
        src = SOURCES[key]
        if key not in cache:
            reader = shifted_pages if src.get("reader") == "shifted" else pages
            cache[key] = [norm(t) for t in reader(PDFS / src["file"])]
        start = next((n for n, t in enumerate(cache[key], 1) if norm(anchor) in t), None)
        if start is None:
            print(f"[{topic}/{kind}] table anchor not found", file=sys.stderr)
            return 1
        found = None
        for n in range(start, min(start + 3, len(cache[key])) + 1):
            if all(norm(v) in cache[key][n - 1] for _, v in cells):
                found = n
                break
        if found is None:
            print(f"[{topic}/{kind}] a cell of {cells[0][1]!r} is not on the table's pages", file=sys.stderr)
            return 1
        passage = " ".join(f"{h}: {norm(v)}." for h, v in cells)
        bad = DENY.search(passage)
        if bad:
            print(f"[{topic}/{kind}] REJECTED: contains {bad.group(0)!r}", file=sys.stderr)
            return 1
        entries.append({
            "topic": topic, "kind": kind, "title": src["title"], "publisher": src["publisher"], "source_url": src["source_url"],
            "published_at": None, "page": found, "excerpt": passage, "verified": False,
        })
        print(f"[{topic}/{kind}] page {found} table row OK: {passage}")
    OUT.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
