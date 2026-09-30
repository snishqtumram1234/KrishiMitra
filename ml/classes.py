"""Class taxonomy and dataset -> KrishiMitra category mapping. Single source of truth for /ml.

Training data: ASDID (healthy / rust / leaf spot) + Mignoni (insect damage only).
The Indian/Maharashtra soybean dataset is HELD-OUT evaluation only and must never appear here.

`unknown` is trained on real soybean problems that fall outside our supported categories
(ASDID bacterial blight, downy mildew, potassium deficiency), so the model can say "not one of mine".
"""

CLASSES = ["healthy", "rust_like", "leaf_spot_like", "insect_damage", "unknown"]

# source key -> category. Source key is "<dataset>/<raw class folder>".
SOURCE_MAP = {
    "asdid/healthy": "healthy",
    "asdid/soybean_rust": "rust_like",
    "asdid/frogeye": "leaf_spot_like",
    "asdid/target_spot": "leaf_spot_like",
    "asdid/cercospora_leaf_blight": "leaf_spot_like",
    "asdid/bacterial_blight": "unknown",
    "asdid/downey_mildew": "unknown",
    "asdid/potassium_deficiency": "unknown",
    "mignoni/caterpillar": "insect_damage",
    "mignoni/diabrotica": "insect_damage",
    # Mignoni "Healthy" is deliberately NOT used (CLAUDE.md: Mignoni = insect damage class only).
}

# Folder-name fragments that mark data we must never train on.
FORBIDDEN_PATH_FRAGMENTS = ("heldout", "held_out", "held-out", "indian", "maharashtra")


def source_caps(images_per_class: int) -> dict[str, int]:
    """Split each category's image budget evenly across the sources that feed it."""
    by_label: dict[str, list[str]] = {}
    for src, label in SOURCE_MAP.items():
        by_label.setdefault(label, []).append(src)
    return {src: max(1, images_per_class // len(srcs)) for srcs in by_label.values() for src in srcs}


def mignoni_source(path_or_name: str) -> str | None:
    """Map a path inside the Mignoni zip to a source key, or None to skip it."""
    p = path_or_name.lower()
    if "caterpillar" in p:
        return "mignoni/caterpillar"
    if "diabrotica" in p:
        return "mignoni/diabrotica"
    return None
