"""Ingested advisory excerpts: verbatim passages with their provenance, verified only by a human decision."""
import importlib.util
import json
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.case import Category
from app.services.advisory_service import AdvisoryService

ENTRY = {
    "topic": "rust_like", "title": "A real bulletin (2023)", "publisher": "A real institute", "source_url": "https://example.org/b.pdf",
    "published_at": None, "page": 53, "excerpt": "Initially chlorotic gray brown spots appear on the leaves.", "verified": False,
}


def service(tmp_path: Path, verification: dict | None = None) -> AdvisoryService:
    f = tmp_path / "excerpts.json"
    f.write_text(json.dumps([ENTRY]), encoding="utf-8")
    if verification is not None:
        (tmp_path / "verification.json").write_text(json.dumps(verification), encoding="utf-8")
    return AdvisoryService(Settings(advisory_excerpts_path=str(f)))


def test_an_excerpt_keeps_its_text_page_and_provenance(tmp_path):
    (src,) = service(tmp_path).retrieve(Category.RUST_LIKE, "Pune").sources
    assert src.source_type == "ingested" and src.excerpt == ENTRY["excerpt"] and src.page == 53
    assert src.publisher == "A real institute" and src.source_url == "https://example.org/b.pdf"
    assert src.published_at is None  # never invented


def test_an_excerpt_is_unverified_unless_a_human_says_so(tmp_path):
    assert service(tmp_path).retrieve(Category.RUST_LIKE, "Pune").sources[0].verified is False
    assert service(tmp_path, {"https://example.org/b.pdf": False}).retrieve(Category.RUST_LIKE, "Pune").sources[0].verified is False
    assert service(tmp_path, {"https://example.org/b.pdf": True}).retrieve(Category.RUST_LIKE, "Pune").sources[0].verified is True


def test_a_label_without_an_excerpt_falls_back_to_a_labelled_demo_source(tmp_path):
    (src,) = service(tmp_path).retrieve(Category.HEALTHY, "Pune").sources
    assert src.source_type == "demo" and src.verified is False and src.excerpt is None


def test_the_service_model_name_says_when_real_excerpts_are_loaded(tmp_path):
    assert service(tmp_path).model_name == "advisory-excerpts"
    assert AdvisoryService(Settings(advisory_excerpts_path="")).model_name == "placeholder-advisory"


def test_treatment_questions_never_get_a_structured_treatment_source(tmp_path):
    svc = service(tmp_path, {"https://example.org/b.pdf": True})
    assert svc.treatment_sources("which pesticide should I use", "Pune").sources == []  # no topic recognised -> nothing
    assert AdvisoryService(Settings(advisory_excerpts_path="")).treatment_sources("rust spray", "Pune").sources == []


def test_a_treatment_question_about_a_known_condition_gets_context_but_never_a_structured_source(tmp_path):
    f = tmp_path / "excerpts.json"
    f.write_text(json.dumps([ENTRY, {**ENTRY, "kind": "management", "excerpt": "Regular monitoring of the field."}]), encoding="utf-8")
    svc = AdvisoryService(Settings(advisory_excerpts_path=str(f)))
    sources = svc.treatment_sources("my rust problem, which treatment?", "Pune").sources
    assert {s.excerpt_kind for s in sources} == {"description", "management"}
    assert all(not s.structured for s in sources)  # so the policy still escalates to an expert; this is only context
    assert {s.excerpt_kind for s in svc.retrieve(Category.RUST_LIKE, "Pune").sources} == {"description", "management"}


def test_topic_words_cover_english_and_marathi():
    from app.services.advisory_service import topic_for_text
    assert topic_for_text("my crops has been eaten by insect") == "insect_damage"
    assert topic_for_text("सोयाबीनवर अळी आली आहे") == "insect_damage"
    assert topic_for_text("rust on leaves") == "rust_like"
    assert topic_for_text("will it rain") is None
    assert topic_for_text("Which pesticide should I spray on soybean rust?") == "rust_like"  # "pesticide" must not mean insects
    assert topic_for_text("which pesticide for my crop") is None
    assert topic_for_text("insect and rust both") is None  # a tie is not guessed


# ---------------------------------------------------------------- the excerpt builder refuses doses and chemicals
def _builder():
    spec = importlib.util.spec_from_file_location("builder", Path(__file__).resolve().parents[1] / "scripts" / "build_advisory_excerpts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("text", [
    "Spray Hexaconazole 5 EC @ 800 ml/ha.",
    "Apply 25 kg/ha of zinc sulphate.",
    "Use recommended chemicals as given in Table 9.",
    "seed treatment with Thiamethoxam",
    "a dose of 2 g per litre",
    "Carbendazim 25% + Mancozeb 50% WS",
])
def test_the_builder_rejects_anything_that_looks_like_a_dose_or_a_chemical(text):
    assert _builder().DENY.search(text)


def test_the_committed_excerpts_contain_no_dose_or_chemical():
    f = Path(__file__).resolve().parents[2] / "data" / "advisories" / "excerpts.json"
    if not f.exists():
        pytest.skip("excerpts not built")
    for e in json.loads(f.read_text(encoding="utf-8")):
        assert not _builder().DENY.search(e["excerpt"]), e["topic"]
        assert e["verified"] is False  # the builder never verifies; that is a human decision
