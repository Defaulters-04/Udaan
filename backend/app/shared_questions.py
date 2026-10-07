"""Shared question options and definitions across Assessment and Intake question banks.

Ensures risk choices, relocation options, time-to-earn options, and canonical career domains
are defined in a single source of truth and cannot drift apart.
All financial amounts are illustrative approximations.
"""

from __future__ import annotations
from dataclasses import dataclass

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


# ---------------------------------------------------------------------------
# 2. Shared Relocation Options (pref_relocation, relocation, guess_relocation)
# ---------------------------------------------------------------------------
RELOCATION_OPTIONS: list[InternalOption] = [
    InternalOption("home_city", "Within our home city / town", "अपने शहर / कस्बे में"),
    InternalOption("same_state", "Within our state", "अपने राज्य में"),
    InternalOption("anywhere_india", "Anywhere in India", "भारत में कहीं भी"),
    InternalOption("abroad_ok", "Abroad / International is fine too", "विदेश जाने में भी कोई आपत्ति नहीं"),
]


# ---------------------------------------------------------------------------
# 3. Shared Time-to-Earn Options (pref_time_to_earn and time_to_earn)
# ---------------------------------------------------------------------------
TIME_TO_EARN_OPTIONS: list[InternalOption] = [
    InternalOption("within_4y", "Within 3 to 4 years (e.g., direct degree or diploma)", "3 से 4 साल के भीतर (जैसे डिग्री या डिप्लोमा के तुरंत बाद)"),
    InternalOption("five_six", "In 5 to 6 years (e.g., professional degree like B.Tech / MBBS / Masters)", "5 से 6 साल में (जैसे बी.टेक, एमबीबीएस या मास्टर्स के बाद)"),
    InternalOption("seven_plus", "7+ years is fine (e.g., advanced research or specialization)", "7 साल या उससे अधिक भी चलेगा (जैसे उच्च शोध या विशेषज्ञता)"),
]


# ---------------------------------------------------------------------------
# 4. Canonical Career Domains (Imported directly from engine/domains.py)
# ---------------------------------------------------------------------------
CAREER_DOMAINS: list[InternalOption] = [
    InternalOption(id=d.id, label_en=d.en, label_hi=d.hi)
    for d in CANONICAL_DOMAINS
]

# Guess domain adds 'not_sure'
GUESS_DOMAIN_OPTIONS: list[InternalOption] = [
    *CAREER_DOMAINS,
    InternalOption("not_sure", "Not sure / Open to anything", "पक्का नहीं पता / किसी भी क्षेत्र में"),
]
