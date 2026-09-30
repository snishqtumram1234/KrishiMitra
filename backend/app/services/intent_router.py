"""Deterministic intent router: English + Marathi keyword rules, no model or LLM call.

Resolution order:
1. Guard intents, in priority order. Any hit wins, because they change what we are allowed to say:
   expert_escalation > treatment_safety > unsupported_request.
2. Topic intents are scored by keyword hits (crop_health_image, weather_context,
   advisory_lookup, general_crop_question). Highest score wins; ties go to the first listed.
   An attached photo adds a point to crop_health_image.
3. Nothing matched: a photo -> crop_health_image (low confidence); no photo -> general question
   with low confidence, which the policy turns into a request for more context.

English terms match whole words ("rain" does not match "grain"). Marathi terms must start a
word but may carry any suffix, so inflected forms (पानांवर, पावसाचा) hit while a term hidden
inside another word does not ("ऊस", sugarcane, must not match "पाऊस", rain).
"""

import re

from app.schemas.orchestration import Intent, IntentResult

GUARDS: list[tuple[Intent, list[str], list[str]]] = [
    (
        Intent.EXPERT_ESCALATION,
        ["expert", "agronomist", "scientist", "agriculture officer", "agri officer", "extension officer",
         "krishi sahayak", "talk to a person", "talk to someone", "call me", "human"],
        ["तज्ञ", "तज्ज्ञ", "कृषी अधिकारी", "कृषी सहाय्यक", "कृषी सहायक", "अधिकाऱ्याशी", "माणसाशी बोल", "फोन करा"],
    ),
    (
        Intent.TREATMENT_SAFETY,
        ["pesticide", "insecticide", "fungicide", "herbicide", "weedicide", "chemical", "spray", "spraying",
         "dose", "dosage", "ml per", "ml/l", "gram per", "per litre", "per liter", "mix in", "how much to spray",
         "which medicine", "what medicine", "treatment", "cure"],
        ["कीटकनाशक", "बुरशीनाशक", "तणनाशक", "फवारणी", "फवारा", "मात्रा", "डोस", "किती मिली", "किती ग्रॅम",
         "औषध", "उपचार", "रसायन"],
    ),
    (
        Intent.UNSUPPORTED_REQUEST,
        ["cotton", "sugarcane", "onion", "tomato", "wheat", "paddy", "rice", "grape", "maize", "tur",
         "loan", "market price", "mandi", "insurance", "subsidy", "scheme", "bank"],
        ["कापूस", "कापस", "ऊस", "उसा", "कांदा", "टोमॅटो", "गहू", "भात", "द्राक्ष", "मका", "तूर", "कर्ज", "बाजारभाव", "बाजार भाव",
         "विमा", "अनुदान", "योजना", "बँक"],
    ),
]

TOPICS: list[tuple[Intent, list[str], list[str]]] = [
    (
        Intent.CROP_HEALTH_IMAGE,
        ["spot", "yellow", "yellowing", "rust", "disease", "leaf", "leaves", "insect", "hole", "worm",
         "caterpillar", "larva", "wilt", "wilting", "pest", "brown", "curl", "curling", "damage", "damaged",
         "blight", "lesion", "photo", "infected", "eaten", "dying", "dry"],
        ["डाग", "ठिपके", "पिवळ", "तांबेरा", "रोग", "पान", "कीड", "अळी", "बुरशी", "छिद्र", "करपा", "सुकत",
         "वाळत", "खाल्ल", "फोटो"],
    ),
    (
        Intent.WEATHER_CONTEXT,
        ["rain", "raining", "rainfall", "forecast", "weather", "temperature", "humidity", "monsoon",
         "storm", "hot", "cold", "wind"],
        ["पाऊस", "पावसा", "हवामान", "अंदाज", "तापमान", "आर्द्रता", "मान्सून", "वादळ", "थंडी", "उष्ण", "वारा"],
    ),
    (
        Intent.ADVISORY_LOOKUP,
        ["advisory", "recommendation", "recommended", "guideline", "official", "kvk", "krishi vigyan",
         "package of practices", "schedule", "bulletin", "university"],
        ["सल्ला", "शिफारस", "मार्गदर्शक", "कृषी विज्ञान केंद्र", "केव्हीके", "विद्यापीठ", "पत्रक"],
    ),
    (
        Intent.GENERAL_CROP_QUESTION,
        ["sow", "sowing", "seed", "seeds", "variety", "spacing", "harvest", "harvesting", "yield",
         "irrigation", "irrigate", "water", "fertilizer", "fertiliser", "soil", "weed", "weeding",
         "flowering", "pod", "pods", "growth", "grow", "germination"],
        ["पेरणी", "बियाणे", "बियाण", "वाण", "काढणी", "उत्पादन", "पाणी", "खत", "माती", "तण", "फुल", "शेंगा",
         "वाढ", "उगवण", "अंतर"],
    ),
]


DEVANAGARI = "ऀ-ॿ"


def _alternation(words: list[str]) -> str:
    return "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))  # longest first


def _compile(en: list[str], mr: list[str]) -> tuple[re.Pattern, re.Pattern]:
    english = re.compile(r"\b(" + _alternation(en) + r")(s|es)?\b", re.IGNORECASE)
    marathi = re.compile(rf"(?<![{DEVANAGARI}])(" + _alternation(mr) + ")")  # word start, any suffix
    return english, marathi


_GUARDS = [(i, *_compile(en, mr)) for i, en, mr in GUARDS]
_TOPICS = [(i, *_compile(en, mr)) for i, en, mr in TOPICS]


def _matches(text: str, english: re.Pattern, marathi: re.Pattern) -> list[str]:
    hits = [m.group(1).lower() for m in english.finditer(text)]
    hits += [m.group(1) for m in marathi.finditer(text)]
    return list(dict.fromkeys(hits))  # unique, keep order


class IntentRouter:
    model_name = "keyword-intent-rules"

    def classify(self, text: str, has_image: bool = False) -> IntentResult:
        text = text or ""

        for intent, pattern, mr in _GUARDS:
            if hits := _matches(text, pattern, mr):
                return IntentResult(intent=intent, confidence=0.95, rule=f"guard:{intent.value}", matched=hits)

        scored = []
        for intent, pattern, mr in _TOPICS:
            hits = _matches(text, pattern, mr)
            score = len(hits) + (1 if intent == Intent.CROP_HEALTH_IMAGE and has_image and hits else 0)
            scored.append((score, intent, hits))
        best_score, best, hits = max(scored, key=lambda s: s[0])  # max keeps the first on ties
        if best_score > 0:
            runner_up = sorted((s for s, _, _ in scored), reverse=True)[1]
            confidence = min(0.95, max(0.5, 0.6 + 0.1 * min(best_score, 3) - 0.1 * runner_up))
            return IntentResult(intent=best, confidence=round(confidence, 2), rule=f"keywords:{best.value}",
                                matched=hits)

        if has_image:
            return IntentResult(intent=Intent.CROP_HEALTH_IMAGE, confidence=0.4, rule="fallback:photo_attached")
        return IntentResult(intent=Intent.GENERAL_CROP_QUESTION, confidence=0.3, rule="fallback:no_match")
