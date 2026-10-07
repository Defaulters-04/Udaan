"""Shared question options and definitions across Assessment and Intake question banks.

Ensures risk choices, relocation options, time-to-earn options, and canonical career domains
are defined in a single source of truth and cannot drift apart.
All financial amounts are illustrative approximations.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from engine.domains import CANONICAL_DOMAINS

QUESTION_BANK_VERSION = "starter-2"


@dataclass(frozen=True)
class InternalOption:
    """Internal representation of a question choice option with bilingual labels."""
    id: str
    label_en: str
    label_hi: str


# ---------------------------------------------------------------------------
# 1. Shared Risk Tasks (pref_risk_1..3 and risk_1..3)
# ---------------------------------------------------------------------------
# All amounts are illustrative.
RISK_GAMBLE_LABEL_EN = "50% chance of ₹10 lakh a year, 50% chance of ₹2 lakh a year (illustrative)"
RISK_GAMBLE_LABEL_HI = "50% संभावना ₹10 लाख प्रति वर्ष की, 50% संभावना ₹2 लाख प्रति वर्ष की (अनुमानित)"

RISK_1_OPTIONS: list[InternalOption] = [
    InternalOption("safe", "₹3.5 lakh a year, guaranteed (illustrative)", "₹3.5 लाख प्रति वर्ष, तय और सुरक्षित (अनुमानित)"),
    InternalOption("gamble", RISK_GAMBLE_LABEL_EN, RISK_GAMBLE_LABEL_HI),
]

RISK_2_OPTIONS: list[InternalOption] = [
    InternalOption("safe", "₹4.5 lakh a year, guaranteed (illustrative)", "₹4.5 लाख प्रति वर्ष, तय और सुरक्षित (अनुमानित)"),
    InternalOption("gamble", RISK_GAMBLE_LABEL_EN, RISK_GAMBLE_LABEL_HI),
]

RISK_3_OPTIONS: list[InternalOption] = [
    InternalOption("safe", "₹5.5 lakh a year, guaranteed (illustrative)", "₹5.5 लाख प्रति वर्ष, तय और सुरक्षित (अनुमानित)"),
    InternalOption("gamble", RISK_GAMBLE_LABEL_EN, RISK_GAMBLE_LABEL_HI),
]


# Edit 1: Shared Risk 3 Prompts
PREF_RISK_3_PROMPT_EN = "Imagine one more pair of starting job offers. Which would you choose?"
PREF_RISK_3_PROMPT_HI = "एक और बार, मान लें कि आपके सामने नौकरी के ये दो विकल्प हैं। आप किसे चुनेंगे?"

# Risk Steps for Mirror display (defined ONCE next to shared risk definition)
RISK_STEPS: list[dict[str, Any]] = [
    {
        "id": "risk_0",
        "label": {
            "en": "Chose the guaranteed offer every time",
            "hi": "हर बार पक्की कमाई वाला विकल्प चुना",
        },
    },
    {
        "id": "risk_1",
        "label": {
            "en": "Chose the gamble once",
            "hi": "एक बार जोखिम वाला विकल्प चुना",
        },
    },
    {
        "id": "risk_2",
        "label": {
            "en": "Chose the gamble twice",
            "hi": "दो बार जोखिम वाला विकल्प चुना",
        },
    },
    {
        "id": "risk_3",
        "label": {
            "en": "Chose the gamble every time",
            "hi": "हर बार जोखिम वाला विकल्प चुना",
        },
    },
]


# ---------------------------------------------------------------------------
# 2. Shared Relocation Options (pref_relocation, relocation, guess_relocation)
# ---------------------------------------------------------------------------
RELOCATION_OPTIONS: list[InternalOption] = [
    InternalOption("home_city", "Within our home city / town", "अपने शहर / कस्बे में"),
    InternalOption("same_state", "Within our state", "अपने राज्य में"),
    InternalOption("anywhere_india", "Anywhere in India", "भारत में कहीं भी"),
    InternalOption("abroad_ok", "Abroad / International is fine too", "विदेश जाने में भी कोई आपत्ति नहीं"),
]

RELOCATION_STEPS: list[dict[str, Any]] = [
    {
        "id": opt.id,
        "label": {"en": opt.label_en, "hi": opt.label_hi},
    }
    for opt in RELOCATION_OPTIONS
]


# ---------------------------------------------------------------------------
# 3. Shared Time-to-Earn Options (pref_time_to_earn and time_to_earn)
# ---------------------------------------------------------------------------
# Edit 2: Updated labels for time_to_earn options
TIME_TO_EARN_OPTIONS: list[InternalOption] = [
    InternalOption(
        "within_4y",
        "About 4 years (e.g., a regular degree, B.Tech or a diploma)",
        "लगभग 4 साल (जैसे सामान्य डिग्री, बी.टेक या डिप्लोमा)",
    ),
    InternalOption(
        "five_six",
        "About 5 to 6 years (e.g., MBBS, 5-year law, or a degree plus a Master's)",
        "लगभग 5 से 6 साल (जैसे एमबीबीएस, 5 साल का लॉ, या डिग्री के बाद मास्टर्स)",
    ),
    InternalOption(
        "seven_plus",
        "7 years or more is fine (e.g., MD/MS or a PhD)",
        "7 साल या उससे ज़्यादा भी चलेगा (जैसे एमडी/एमएस या पीएचडी)",
    ),
]

TIME_TO_EARN_STEPS: list[dict[str, Any]] = [
    {
        "id": opt.id,
        "label": {"en": opt.label_en, "hi": opt.label_hi},
    }
    for opt in TIME_TO_EARN_OPTIONS
]


# ---------------------------------------------------------------------------
# 4. Canonical Career Domains (Imported directly from engine/domains.py)
# ---------------------------------------------------------------------------
CAREER_DOMAINS: list[InternalOption] = [
    InternalOption(id=d.id, label_en=d.en, label_hi=d.hi)
    for d in CANONICAL_DOMAINS
]

MIRROR_DOMAIN_OPTIONS: list[dict[str, Any]] = [
    {
        "id": d.id,
        "label": {"en": d.en, "hi": d.hi},
    }
    for d in CANONICAL_DOMAINS
]

# Guess domain adds 'not_sure'
GUESS_DOMAIN_OPTIONS: list[InternalOption] = [
    *CAREER_DOMAINS,
    InternalOption("not_sure", "Not sure / Open to anything", "पक्का नहीं पता / किसी भी क्षेत्र में"),
]
