import re

import pytest
from conftest import GOOD_JPEG

from app.config import Settings
from app.schemas.case import CaseInput, Category, DecisionState
from app.schemas.orchestration import Intent
from app.services.intent_router import IntentRouter
from app.services.orchestrator import Orchestrator
from app.services.vision_service import FakeVisionService

router = IntentRouter()

EXAMPLES = {
    Intent.CROP_HEALTH_IMAGE: [
        "There are yellow spots on the leaves",
        "Brown lesions spreading on soybean leaf",
        "Caterpillars are eating holes in the leaves",
        "पानांवर पिवळे डाग आले आहेत",  # yellow spots have appeared on the leaves
        "सोयाबीनच्या पानांना छिद्र पडली आहेत, अळी दिसते",  # holes in soybean leaves, larva visible
        "पाने सुकत आहेत",  # leaves are drying
    ],
    Intent.WEATHER_CONTEXT: [
        "Will it rain in my area?",
        "What is the weather forecast for this week?",
        "Is humidity going to be high tomorrow?",
        "उद्या पाऊस पडेल का?",  # will it rain tomorrow?
        "या आठवड्याचा हवामान अंदाज काय आहे?",  # what is this week's weather forecast?
        "तापमान किती असेल?",  # what will the temperature be?
    ],
    Intent.ADVISORY_LOOKUP: [
        "Show me the latest KVK advisory for soybean",
        "What is the official recommendation for soybean in Pune?",
        "Is there a university bulletin on soybean?",
        "सोयाबीनसाठी कृषी विज्ञान केंद्राचा सल्ला सांगा",  # tell me the KVK advice for soybean
        "सोयाबीनची शिफारस केलेली पद्धत कोणती?",  # what is the recommended method for soybean?
    ],
    Intent.GENERAL_CROP_QUESTION: [
        "When should I sow soybean?",
        "What is the right spacing between rows?",
        "Which variety gives the best yield?",
        "सोयाबीनची पेरणी कधी करावी?",  # when should soybean be sown?
        "कोणते वाण चांगले आहे?",  # which variety is good?
        "पाणी किती द्यावे?",  # how much water should I give?
    ],
    Intent.TREATMENT_SAFETY: [
        "Which pesticide and how much?",
        "What fungicide should I spray for rust?",
        "Tell me the dosage per litre",
        "कोणते कीटकनाशक फवारावे?",  # which insecticide should I spray?
        "बुरशीनाशकाची मात्रा किती?",  # what is the fungicide dose?
        "तांबेरा रोगासाठी कोणते औषध वापरू?",  # which medicine should I use for rust?
    ],
    Intent.EXPERT_ESCALATION: [
        "I want to talk to an expert",
        "Please connect me with the agriculture officer",
        "Can a human agronomist look at my field?",
        "मला तज्ञांशी बोलायचे आहे",  # I want to talk to experts
        "कृषी अधिकारी यांना फोन करा",  # call the agriculture officer
    ],
    Intent.UNSUPPORTED_REQUEST: [
        "My cotton leaves have spots",
        "What is today's soybean market price?",
        "How do I get a crop loan?",
        "कापसावर कीड आली आहे",  # pests on cotton
        "पीक विमा कसा मिळेल?",  # how do I get crop insurance?
        "सोयाबीनचा बाजारभाव काय आहे?",  # what is the soybean market price?
    ],
}
CASES = [(intent, text) for intent, texts in EXAMPLES.items() for text in texts]


def test_at_least_five_examples_per_intent_with_marathi():
    devanagari = re.compile(r"[ऀ-ॿ]")
    assert set(EXAMPLES) == set(Intent)
    for intent, texts in EXAMPLES.items():
        assert len(texts) >= 5, intent
        assert any(devanagari.search(t) for t in texts), f"no Marathi example for {intent}"


@pytest.mark.parametrize("expected,text", CASES, ids=[f"{i.value}:{t[:30]}" for i, t in CASES])
def test_classifies_example(expected, text):
    r = router.classify(text)
    assert r.intent == expected, (r.intent, r.rule, r.matched)
    assert r.matched and 0.5 <= r.confidence <= 1.0
    assert r.rule.endswith(expected.value)


# ---------------------------------------------------------------- rule mechanics
def test_guards_beat_topics_and_are_ordered():
    assert router.classify("yellow spots, which pesticide should I spray?").intent == Intent.TREATMENT_SAFETY
    assert router.classify("I need an expert to tell me the spray dose").intent == Intent.EXPERT_ESCALATION
    assert router.classify("which pesticide for my cotton?").intent == Intent.TREATMENT_SAFETY


def test_symptoms_after_rain_are_crop_health_not_weather():
    r = router.classify("Heavy rain last week and now yellow spots on the leaves")
    assert r.intent == Intent.CROP_HEALTH_IMAGE


def test_word_boundaries_prevent_false_hits():
    # "grain" must not match "rain", "whole" must not match "hole", "photographer" must not match "photo"
    assert router.classify("the whole grain store").rule == "fallback:no_match"


def test_marathi_term_inside_another_word_does_not_match():
    # ऊस (sugarcane) sits inside पाऊस (rain): must not turn a weather question into "unsupported crop"
    assert router.classify("पाऊस").intent == Intent.WEATHER_CONTEXT
    assert router.classify("उसाच्या पानांवर डाग").intent == Intent.UNSUPPORTED_REQUEST  # inflected sugarcane
    assert router.classify("कापसावर डाग").intent == Intent.UNSUPPORTED_REQUEST  # inflected cotton


def test_photo_breaks_ties_toward_crop_health():
    text = "leaf problem after rain"  # 1 crop-health hit, 1 weather hit
    assert router.classify(text, has_image=True).intent == Intent.CROP_HEALTH_IMAGE


def test_fallbacks():
    with_photo = router.classify("hello", has_image=True)
    assert with_photo.intent == Intent.CROP_HEALTH_IMAGE and with_photo.rule == "fallback:photo_attached"
    no_photo = router.classify("hello")
    assert no_photo.rule == "fallback:no_match" and no_photo.confidence < 0.5
    assert router.classify("").rule == "fallback:no_match"


def test_confidence_reflects_agreement():
    strong = router.classify("yellow spots and holes on the leaves")
    mixed = router.classify("leaf spots after rain")
    assert strong.confidence > mixed.confidence


# ---------------------------------------------------------------- each intent takes its own path
def orch(conf=0.95):
    return Orchestrator(Settings(), vision=FakeVisionService(label=Category.RUST_LIKE, confidence=conf))


def ask(text, image=None):
    return orch().run(CaseInput(crop="soybean", symptom_context=text, close_up_image=image))


def steps(r):
    return [c.route for c in r.calls]


@pytest.mark.parametrize("image", [None, GOOD_JPEG], ids=["no_photo", "with_photo"])
def test_weather_question_never_calls_vision(image):
    r = ask("Will it rain in my area?", image)
    assert r.intent == Intent.WEATHER_CONTEXT and r.path == "weather"
    assert steps(r) == ["intent_router", "weather"]
    assert "vision" in r.skipped_steps and "quality_gate" in r.skipped_steps
    assert r.state == DecisionState.PRELIMINARY_GUIDANCE


@pytest.mark.parametrize("text", EXAMPLES[Intent.TREATMENT_SAFETY])
def test_treatment_question_never_produces_a_dose(text):
    r = ask(text, GOOD_JPEG)
    assert r.intent == Intent.TREATMENT_SAFETY and r.path == "treatment_safety"
    assert r.state == DecisionState.EXPERT_REVIEW  # no verified structured source exists yet
    assert "vision" not in steps(r)
    msg = r.message.lower()
    assert "does not give pesticide names or doses" in msg
    assert not re.search(r"\d", msg), "a number in a treatment answer could be read as a dose"
    for unit in (" ml", "litre", "liter", "gram", " kg", "per acre", "%"):
        assert unit not in msg


@pytest.mark.parametrize("text", EXAMPLES[Intent.EXPERT_ESCALATION])
def test_expert_request_goes_straight_to_expert(text):
    r = ask(text, GOOD_JPEG)
    assert r.state == DecisionState.EXPERT_REVIEW and r.reason == "farmer_requested_expert"
    assert steps(r) == ["intent_router"]


@pytest.mark.parametrize("text", EXAMPLES[Intent.UNSUPPORTED_REQUEST])
def test_unsupported_request_stops(text):
    r = ask(text, GOOD_JPEG)
    assert r.state == DecisionState.UNSUPPORTED and steps(r) == ["intent_router"]


@pytest.mark.parametrize("intent", [Intent.ADVISORY_LOOKUP, Intent.GENERAL_CROP_QUESTION])
def test_text_questions_use_advisory_not_vision(intent):
    r = ask(EXAMPLES[intent][0], GOOD_JPEG)
    assert r.path == intent.value and steps(r) == ["intent_router", "advisory"]
    assert r.state == DecisionState.PRELIMINARY_GUIDANCE and r.sources


def test_crop_health_uses_the_image_path():
    r = ask(EXAMPLES[Intent.CROP_HEALTH_IMAGE][0], GOOD_JPEG)
    assert r.path == "image_diagnosis"
    assert steps(r) == ["intent_router", "quality_gate", "vision", "advisory", "weather"]


def test_intent_is_recorded_on_result():
    r = ask("उद्या पाऊस पडेल का?")
    assert r.intent == Intent.WEATHER_CONTEXT
    assert r.intent_rule == "keywords:weather_context" and r.intent_confidence >= 0.5
    assert r.calls[0].output["matched"] == ["पाऊस"]
