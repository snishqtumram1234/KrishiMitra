"""API.md must describe everything the code exposes. Fails when code and docs drift apart."""

import re
from pathlib import Path

import pytest

from app.main import app
from app.schemas.api import ImageKind
from app.schemas.case import Category, DecisionState
from app.schemas.expert import ExpertStatus, ReviewDecision
from app.schemas.orchestration import Intent
from app.services.metrics_service import STEP_TIER
from app.services.quality_gate import NEXT_ACTION

ROOT = Path(__file__).resolve().parents[2]
DOC = (ROOT / "API.md").read_text(encoding="utf-8")
SPEC = app.openapi()
APP_DIR = ROOT / "backend" / "app"
PUBLIC_DOC_ROUTES = {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}


def test_every_endpoint_is_documented():
    missing = []
    for path, ops in SPEC["paths"].items():
        for method in ops:
            if f"{method.upper()} {path}" not in DOC and f"`{path}`" not in DOC:
                missing.append(f"{method.upper()} {path}")
    assert not missing, f"endpoints missing from API.md: {missing}"


def test_endpoint_index_lists_every_method_and_url():
    """The index table has one `| METHOD | `url` |` row per operation."""
    rows = set(re.findall(r"^\| (GET|POST|PUT|PATCH|DELETE) \| `([^`]+)`", DOC, flags=re.M))
    expected = {(m.upper(), p) for p, ops in SPEC["paths"].items() for m in ops}
    assert expected <= rows, f"missing from the endpoint index: {sorted(expected - rows)}"


@pytest.mark.parametrize("enum", [DecisionState, Intent, Category, ImageKind, ExpertStatus, ReviewDecision])
def test_every_enum_value_is_documented(enum):
    missing = [v.value for v in enum if f"`{v.value}`" not in DOC]
    assert not missing, f"{enum.__name__} values missing from API.md: {missing}"


def test_every_step_name_is_documented():
    assert [s for s in STEP_TIER if f"`{s}`" not in DOC] == []


def test_every_route_name_is_documented():
    """Paths the orchestrator can set: literal ctx['path'] values plus the intent values used as paths."""
    src = (APP_DIR / "services" / "orchestrator.py").read_text(encoding="utf-8")
    paths = set(re.findall(r'ctx\["path"\] = "(\w+)"', src)) | {
        Intent.EXPERT_ESCALATION.value, Intent.UNSUPPORTED_REQUEST.value,
        Intent.ADVISORY_LOOKUP.value, Intent.GENERAL_CROP_QUESTION.value,
    }
    assert {"image_diagnosis", "weather", "treatment_safety"} <= paths
    assert [p for p in sorted(paths) if f"| `{p}` |" not in DOC] == []
    assert "`none`" in DOC  # the stored path for a non-soybean crop


def test_every_decision_reason_is_documented():
    src = (APP_DIR / "services" / "policy_engine.py").read_text(encoding="utf-8")
    literal = set(re.findall(r'reason="([a-z_]+)"', src))
    assert "mid_confidence" in literal and "treatment_needs_expert" in literal
    assert [r for r in sorted(literal) if f"`{r}`" not in DOC] == []
    for prefix in ("quality:", "sources_unavailable:"):
        assert f"`{prefix}<" in DOC


def test_every_quality_issue_and_next_action_is_documented():
    assert [i for i in NEXT_ACTION if f"`{i}`" not in DOC] == []
    assert [a for a in NEXT_ACTION.values() if f"`{a}`" not in DOC] == []


def test_every_intent_rule_kind_is_documented():
    for kind in ("guard:<intent>", "keywords:<intent>", "fallback:photo_attached", "fallback:no_match"):
        assert kind in DOC


def test_every_schema_has_a_section():
    names = set(SPEC["components"]["schemas"]) - {"HTTPValidationError", "ValidationError"}
    names = {n for n in names if not n.startswith("Body_")}
    headings = set(re.findall(r"^#{3,4} (\w+)\s*$", DOC, flags=re.M)) | set(re.findall(r"^- `(\w+)`:", DOC, flags=re.M))
    assert sorted(names - headings) == []


def test_documented_fields_match_the_models():
    """Spot-check that field names of the main response models appear in their schema block."""
    for name in ("CaseAnalysisOut", "OrchestratorResult", "RunTrace", "WeatherResult", "ExpertReviewRecord", "Overview"):
        props = SPEC["components"]["schemas"][name]["properties"]
        block = DOC.split(f"#### {name}\n", 1)[1].split("```\n", 1)[0]  # the ```ts block under the heading
        assert [p for p in props if f"  {p}" not in block] == [], name


def test_auth_facts_match_the_code():
    from app.api import auth

    assert auth.AUDIENCE == "authenticated" and '`aud` must be `authenticated`' in DOC
    assert auth.EXPERT_ROLE in DOC and "app_metadata.role" in DOC
    assert "`user_metadata`" in DOC
