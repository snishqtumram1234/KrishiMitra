import pytest
from pydantic import ValidationError

from app.config import Settings
from app.schemas.case import Category, DecisionState
from app.schemas.orchestration import (
    AdvisoryResult,
    AdvisorySource,
    Intent,
    IntentResult,
    QualityResult,
    Tier,
    VisionResult,
    WeatherResult,
)
from app.services.policy_engine import PolicyEngine

policy = PolicyEngine(Settings())


def vr(label: Category, conf: float, name: str = "m") -> VisionResult:
    return VisionResult(model_name=name, label=label, confidence=conf)


ADVISORY = AdvisoryResult(
    sources=[AdvisorySource(title="t", publisher="p", verified=True, source_type="ingested")], summary="Summary."
)


# ---- thresholds
@pytest.mark.parametrize(
    "conf,expected",
    [
        (0.0, Tier.LOW),
        (0.59, Tier.LOW),
        (0.5999, Tier.LOW),
        (0.60, Tier.MID),
        (0.72, Tier.MID),
        (0.85, Tier.MID),
        (0.8501, Tier.HIGH),
        (0.95, Tier.HIGH),
        (1.0, Tier.HIGH),
    ],
)
def test_tier_boundaries(conf, expected):
    assert policy.tier(conf) == expected


def test_default_thresholds_match_claude_md():
    assert (policy.low, policy.high) == (0.60, 0.85)


def test_custom_thresholds_are_respected():
    p = PolicyEngine(Settings(vision_low_confidence=0.5, vision_high_confidence=0.9))
    assert p.tier(0.55) == Tier.MID
    assert p.tier(0.9) == Tier.MID
    assert p.tier(0.91) == Tier.HIGH


@pytest.mark.parametrize("low,high", [(0.9, 0.6), (0.7, 0.7), (-0.1, 0.8), (0.5, 1.5)])
def test_invalid_thresholds_rejected(low, high):
    with pytest.raises(ValueError):
        PolicyEngine(Settings(vision_low_confidence=low, vision_high_confidence=high))


@pytest.mark.parametrize("bad", [-0.01, 1.01])
def test_confidence_outside_unit_range_rejected(bad):
    with pytest.raises(ValidationError):
        vr(Category.RUST_LIKE, bad)


# ---- pre-vision checks
def test_quality_pass_continues_fail_blocks():
    assert policy.check_quality(QualityResult(passed=True, score=90)) is None
    d = policy.check_quality(QualityResult(passed=False, score=10, issues=["blurry"], next_action="retake_steady"))
    assert d.state == DecisionState.NEEDS_BETTER_IMAGE
    assert "blurry" in d.reason
    assert "hold the phone steady" in d.message


def test_quality_message_combines_up_to_two_tips():
    d = policy.check_quality(QualityResult(passed=False, score=5, issues=["too_dark", "blurry", "too_small"]))
    assert "daylight" in d.message and "steady" in d.message and "move closer" not in d.message


@pytest.mark.parametrize("crop", ["soybean", "Soybean", "  SOYBEAN "])
def test_soybean_accepted(crop):
    assert policy.check_crop(crop) is None


@pytest.mark.parametrize("crop", ["cotton", "", "soybean-like"])
def test_other_crops_unsupported(crop):
    assert policy.check_crop(crop).state == DecisionState.UNSUPPORTED


def ir(intent, conf=0.9, rule="test"):
    return IntentResult(intent=intent, confidence=conf, rule=rule)


def test_check_intent_terminal_intents():
    assert policy.check_intent(ir(Intent.EXPERT_ESCALATION)).state == DecisionState.EXPERT_REVIEW
    assert policy.check_intent(ir(Intent.UNSUPPORTED_REQUEST)).state == DecisionState.UNSUPPORTED
    unclear = policy.check_intent(ir(Intent.GENERAL_CROP_QUESTION, conf=0.3))
    assert unclear.state == DecisionState.NEEDS_MORE_CONTEXT and unclear.follow_up_question


@pytest.mark.parametrize("intent", [Intent.CROP_HEALTH_IMAGE, Intent.WEATHER_CONTEXT, Intent.ADVISORY_LOOKUP,
                                    Intent.GENERAL_CROP_QUESTION, Intent.TREATMENT_SAFETY])
def test_check_intent_lets_path_intents_through(intent):
    assert policy.check_intent(ir(intent)) is None


def test_low_confidence_photo_intent_still_goes_to_image_path():
    assert policy.check_intent(ir(Intent.CROP_HEALTH_IMAGE, conf=0.4)) is None


def test_treatment_without_verified_structured_source_escalates():
    for sources in (None, AdvisoryResult(), ADVISORY):  # ADVISORY is verified but not structured
        d = policy.decide_treatment(sources)
        assert d.state == DecisionState.EXPERT_REVIEW and d.reason == "treatment_needs_expert"
        assert "does not give pesticide names or doses" in d.message


def test_treatment_with_verified_structured_source_points_to_it_without_a_dose():
    src = AdvisoryResult(sources=[AdvisorySource(title="Soybean rust IPM card", publisher="ICAR-IISR",
                                                 verified=True, source_type="ingested", structured=True)])
    d = policy.decide_treatment(src)
    assert d.state == DecisionState.PRELIMINARY_GUIDANCE
    assert "Soybean rust IPM card (ICAR-IISR)" in d.message and "does not give" in d.message


def test_stale_or_unverified_structured_sources_do_not_count():
    for s in (AdvisorySource(title="t", publisher="p", verified=True, source_type="ingested", structured=True, stale=True),
              AdvisorySource(title="t", publisher="p", verified=False, structured=True)):
        assert policy.decide_treatment(AdvisoryResult(sources=[s])).state == DecisionState.EXPERT_REVIEW


def test_weather_and_text_answers():
    assert policy.decide_weather(WeatherResult(available=True, summary="Rain likely.")).state ==         DecisionState.PRELIMINARY_GUIDANCE
    assert policy.decide_weather(WeatherResult(available=False)).state == DecisionState.EXPERT_REVIEW
    assert policy.decide_weather(None).state == DecisionState.EXPERT_REVIEW
    assert policy.decide_text_answer(Intent.ADVISORY_LOOKUP, ADVISORY).reason == "advisory_lookup"
    assert policy.decide_text_answer(Intent.GENERAL_CROP_QUESTION, None).state == DecisionState.EXPERT_REVIEW


# ---- model results
def test_pick_top_takes_highest_confidence():
    top = policy.pick_top([vr(Category.HEALTHY, 0.4), vr(Category.RUST_LIKE, 0.9)])
    assert top.label == Category.RUST_LIKE


def test_models_conflict():
    assert not policy.models_conflict([vr(Category.RUST_LIKE, 0.9), vr(Category.RUST_LIKE, 0.7)])
    assert policy.models_conflict([vr(Category.RUST_LIKE, 0.9), vr(Category.HEALTHY, 0.9)])
    assert not policy.models_conflict([vr(Category.RUST_LIKE, 0.9)])


# ---- decisions
def test_low_asks_for_evidence_first_then_escalates():
    first = policy.decide_low(has_field_overview=False)
    assert first.state == DecisionState.NEEDS_MORE_CONTEXT
    assert first.follow_up_question
    assert policy.decide_low(has_field_overview=True).state == DecisionState.EXPERT_REVIEW


def test_escalation_decisions():
    assert policy.decide_conflict().state == DecisionState.EXPERT_REVIEW
    assert policy.decide_unknown_label().state == DecisionState.EXPERT_REVIEW
    d = policy.decide_sources_missing("weather")
    assert d.state == DecisionState.EXPERT_REVIEW
    assert "weather" in d.reason


def test_mid_guidance_has_follow_up_and_no_treatment():
    d = policy.decide_guidance(Tier.MID, Category.RUST_LIKE, ADVISORY, None)
    assert d.state == DecisionState.PRELIMINARY_GUIDANCE
    assert d.follow_up_question
    assert "No treatment" in d.message


def test_high_guidance_includes_weather_and_defers_to_officer():
    w = WeatherResult(available=True, summary="Rain expected.")
    d = policy.decide_guidance(Tier.HIGH, Category.LEAF_SPOT_LIKE, ADVISORY, w)
    assert d.state == DecisionState.PRELIMINARY_GUIDANCE
    assert "Rain expected." in d.message
    assert "agriculture officer" in d.message
    assert d.follow_up_question is None


@pytest.mark.parametrize("tier", [Tier.MID, Tier.HIGH])
@pytest.mark.parametrize("label", list(Category))
def test_guidance_never_a_confirmed_diagnosis_or_dosage(tier, label):
    d = policy.decide_guidance(tier, label, ADVISORY, WeatherResult(available=True))
    msg = d.message.lower()
    assert "not a confirmed diagnosis" in msg
    for banned in ["dose", "dosage", " ml", " gram", "per litre", "per liter", "spray"]:
        assert banned not in msg


def test_policy_engine_can_produce_every_decision_state():
    """Guard: if a DecisionState is added, some policy path must produce it."""
    produced = {
        policy.check_quality(QualityResult(passed=False, score=0, issues=["blurry"])).state,
        policy.check_crop("cotton").state,
        policy.check_intent(ir(Intent.UNSUPPORTED_REQUEST)).state,
        policy.check_intent(ir(Intent.GENERAL_CROP_QUESTION, conf=0.3)).state,
        policy.decide_low(has_field_overview=False).state,
        policy.decide_low(has_field_overview=True).state,
        policy.decide_conflict().state,
        policy.decide_unknown_label().state,
        policy.decide_sources_missing("x").state,
        policy.decide_guidance(Tier.MID, Category.RUST_LIKE, ADVISORY, None).state,
        policy.decide_guidance(Tier.HIGH, Category.RUST_LIKE, ADVISORY, WeatherResult(available=True)).state,
    }
    assert produced == set(DecisionState)


# ---- AdvisoryResult / WeatherResult usability
def test_advisory_usable_rules():
    assert ADVISORY.usable
    assert not AdvisoryResult().usable  # no sources
    unverified = AdvisoryResult(sources=[AdvisorySource(title="t", publisher="p", verified=False)])
    stale = AdvisoryResult(sources=[AdvisorySource(title="t", publisher="p", verified=True, source_type="ingested", stale=True)])
    assert not unverified.usable
    assert not stale.usable


def test_weather_usable_rules():
    assert WeatherResult(available=True).usable
    assert not WeatherResult(available=False).usable
    assert not WeatherResult(available=True, stale=True).usable
