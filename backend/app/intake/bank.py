# Parent Intake Question Bank (16 questions across 5 sections, Version: starter-2).
# All financial amounts are illustrative approximations.

from dataclasses import dataclass, field
from typing import Any, Optional

from app.shared_questions import (
    CAREER_DOMAINS,
    GUESS_DOMAIN_OPTIONS,
    InternalOption,
    PREF_RISK_3_PROMPT_EN,
    PREF_RISK_3_PROMPT_HI,
    RELOCATION_OPTIONS,
    RISK_1_OPTIONS,
    RISK_2_OPTIONS,
    RISK_3_OPTIONS,
    TIME_TO_EARN_OPTIONS,
)

QUESTION_BANK_VERSION = "starter-2"


@dataclass(frozen=True)
class InternalQuestion:
    id: str
    type: str
    prompt_en: str
    prompt_hi: str
    required: bool
    tag: str  # Internal tag, never returned publicly
    options: list[InternalOption] = field(default_factory=list)
    min: Optional[int] = None
    max: Optional[int] = None
    min_label_en: Optional[str] = None
    min_label_hi: Optional[str] = None
    max_label_en: Optional[str] = None
    max_label_hi: Optional[str] = None
    max_length: Optional[int] = None
    placeholder_en: Optional[str] = None
    placeholder_hi: Optional[str] = None
    max_select: Optional[int] = None


@dataclass(frozen=True)
class InternalSection:
    id: str
    title_en: str
    title_hi: str
    questions: list[InternalQuestion]


PUBLIC_QUESTION_ALLOWED_KEYS = {
    "id",
    "type",
    "prompt",
    "required",
    "options",
    "min",
    "max",
    "min_label",
    "max_label",
    "max_length",
    "placeholder",
    "max_select",
}

# 1. Money Section (5 items, all financial amounts marked illustrative)
MONEY_QUESTIONS: list[InternalQuestion] = [
    InternalQuestion(
        id="income_band",
        type="single_choice",
        prompt_en="What is your approximate annual family income?",
        prompt_hi="आपके परिवार की लगभग वार्षिक आय कितनी है?",
        required=True,
        tag="income",
        # Illustrative amounts
        options=[
            InternalOption("under_3l", "Under ₹3 lakh (illustrative)", "₹3 लाख से कम (अनुमानित)"),
            InternalOption("3_6l", "₹3 lakh to ₹6 lakh (illustrative)", "₹3 लाख से ₹6 लाख (अनुमानित)"),
            InternalOption("6_12l", "₹6 lakh to ₹12 lakh (illustrative)", "₹6 लाख से ₹12 लाख (अनुमानित)"),
            InternalOption("12_25l", "₹12 lakh to ₹25 lakh (illustrative)", "₹12 लाख से ₹25 लाख (अनुमानित)"),
            InternalOption("over_25l", "Over ₹25 lakh (illustrative)", "₹25 लाख से अधिक (अनुमानित)"),
        ],
    ),
    InternalQuestion(
        id="savings_band",
        type="single_choice",
        prompt_en="How much savings have you set aside for your child's higher education?",
        prompt_hi="आपने बच्चे की उच्च शिक्षा के लिए लगभग कितनी बचत रखी है?",
        required=True,
        tag="savings",
        # Illustrative amounts
        options=[
            InternalOption("none", "No dedicated savings yet", "अभी कोई अलग बचत नहीं है"),
            InternalOption("under_1l", "Under ₹1 lakh (illustrative)", "₹1 लाख से कम (अनुमानित)"),
            InternalOption("1_3l", "₹1 lakh to ₹3 lakh (illustrative)", "₹1 लाख से ₹3 लाख (अनुमानित)"),
            InternalOption("3_8l", "₹3 lakh to ₹8 lakh (illustrative)", "₹3 लाख से ₹8 लाख (अनुमानित)"),
            InternalOption("over_8l", "Over ₹8 lakh (illustrative)", "₹8 लाख से अधिक (अनुमानित)"),
        ],
    ),
    InternalQuestion(
        id="loan_band",
        type="single_choice",
        prompt_en="What amount of education loan would your family feel comfortable taking?",
        prompt_hi="आपकी पारिवारिक स्थिति के अनुसार आप कितना शिक्षा ऋण (लोन) लेने में सहज हैं?",
        required=True,
        tag="loan",
        # Illustrative amounts
        options=[
            InternalOption("none", "Prefer no loan at all", "लोन बिल्कुल नहीं लेना चाहते"),
            InternalOption("up_to_3l", "Up to ₹3 lakh (illustrative)", "₹3 लाख तक (अनुमानित)"),
            InternalOption("3_8l", "₹3 lakh to ₹8 lakh (illustrative)", "₹3 लाख से ₹8 लाख (अनुमानित)"),
            InternalOption("8_15l", "₹8 lakh to ₹15 lakh (illustrative)", "₹8 लाख से ₹15 लाख (अनुमानित)"),
            InternalOption("over_15l", "Over ₹15 lakh (illustrative)", "₹15 लाख से अधिक (अनुमानित)"),
        ],
    ),
    InternalQuestion(
        id="surplus_band",
        type="single_choice",
        prompt_en="How much money is left over each month after all expenses?",
        prompt_hi="हर महीने सारे खर्चों के बाद परिवार के पास लगभग कितनी बचत बचती है?",
        required=True,
        tag="surplus",
        # All rupee amounts are illustrative
        options=[
            InternalOption("none", "None", "कुछ नहीं"),
            InternalOption("under_5k", "Under ₹5,000 (illustrative)", "₹5,000 से कम (अनुमानित)"),
            InternalOption("5k_15k", "₹5,000 to ₹15,000 (illustrative)", "₹5,000 से ₹15,000 (अनुमानित)"),
            InternalOption("15k_30k", "₹15,000 to ₹30,000 (illustrative)", "₹15,000 से ₹30,000 (अनुमानित)"),
            InternalOption("over_30k", "Over ₹30,000 (illustrative)", "₹30,000 से अधिक (अनुमानित)"),
        ],
    ),
    InternalQuestion(
        id="emi_band",
        type="single_choice",
        prompt_en="What total loan EMIs does the family already pay each month?",
        prompt_hi="परिवार हर महीने कुल कितनी लोन ईएमआई (EMI) भरता है?",
        required=True,
        tag="emi",
        # All rupee amounts are illustrative
        options=[
            InternalOption("none", "None", "कोई ईएमआई नहीं"),
            InternalOption("under_5k", "Under ₹5,000 (illustrative)", "₹5,000 से कम (अनुमानित)"),
            InternalOption("5k_15k", "₹5,000 to ₹15,000 (illustrative)", "₹5,000 से ₹15,000 (अनुमानित)"),
            InternalOption("over_15k", "Over ₹15,000 (illustrative)", "₹15,000 से अधिक (अनुमानित)"),
        ],
    ),
]

# 2. Risk Section (3 items, shared options)
RISK_QUESTIONS: list[InternalQuestion] = [
    InternalQuestion(
        id="risk_1",
        type="single_choice",
        prompt_en="Imagine two starting job offers for your child after college. Which would you prefer they choose?",
        prompt_hi="कल्पना करें कि कॉलेज के बाद आपके बच्चे के सामने नौकरी के दो विकल्प हैं। आप किसे प्राथमिकता देंगे?",
        required=True,
        tag="risk",
        options=RISK_1_OPTIONS,
    ),
    InternalQuestion(
        id="risk_2",
        type="single_choice",
        prompt_en="Imagine a different set of starting job offers for your child. Which would you prefer they choose?",
        prompt_hi="अब मान लें कि आपके बच्चे के सामने ये दो विकल्प हैं। आप किसे बेहतर मानेंगे?",
        required=True,
        tag="risk",
        options=RISK_2_OPTIONS,
    ),
    InternalQuestion(
        id="risk_3",
        type="single_choice",
        prompt_en=PREF_RISK_3_PROMPT_EN,
        prompt_hi=PREF_RISK_3_PROMPT_HI,
        required=True,
        tag="risk",
        options=RISK_3_OPTIONS,
    ),
]

# 3. Plans Section (2 items, shared options)
PLANS_QUESTIONS: list[InternalQuestion] = [
    InternalQuestion(
        id="relocation",
        type="single_choice",
        prompt_en="How far are you comfortable sending your child for higher studies or work?",
        prompt_hi="पढ़ाई या नौकरी के लिए आप अपने बच्चे को कितनी दूर भेजने में सहज हैं?",
        required=True,
        tag="relocation",
        options=RELOCATION_OPTIONS,
    ),
    InternalQuestion(
        id="time_to_earn",
        type="single_choice",
        prompt_en="How soon do you expect your child to start earning after completing school?",
        prompt_hi="स्कूल पूरा करने के बाद आप बच्चे से कब तक कमाई शुरू करने की उम्मीद करते हैं?",
        required=True,
        tag="time_to_earn",
        options=TIME_TO_EARN_OPTIONS,
    ),
]

# 4. Hopes Section (3 items)
HOPES_QUESTIONS: list[InternalQuestion] = [
    InternalQuestion(
        id="domain_wish",
        type="multi_choice",
        prompt_en="Which career domains do you hope your child considers? (Pick up to 3)",
        prompt_hi="आप किन क्षेत्रों में अपने बच्चे के जाने की उम्मीद रखते हैं? (अधिकतम 3 चुनें)",
        required=True,
        tag="domain_wish",
        max_select=3,
        options=CAREER_DOMAINS,
    ),
    InternalQuestion(
        id="non_negotiables",
        type="multi_choice",
        prompt_en="Are there any factors you consider non-negotiable for their career?",
        prompt_hi="क्या ऐसी कोई बातें हैं जिन पर आप बिल्कुल समझौता नहीं करना चाहते?",
        required=False,
        tag="non_negotiables",
        options=[
            InternalOption("near_home", "Must stay close to family", "परिवार के पास रहना जरूरी"),
            InternalOption("job_security", "High job security is essential", "नौकरी की सुरक्षा सबसे जरूरी"),
            InternalOption("govt_or_public", "Government or public sector preferred", "सरकारी या सार्वजनिक क्षेत्र को प्राथमिकता"),
            InternalOption("low_loan", "Must avoid heavy education debt", "भारी कर्ज से बचना जरूरी"),
        ],
    ),
    InternalQuestion(
        id="hope_text",
        type="long_text",
        prompt_en="In your own words, what is your biggest hope or dream for your child's future?",
        prompt_hi="अपने शब्दों में बताएं, अपने बच्चे के भविष्य के लिए आपकी सबसे बड़ी उम्मीद या सपना क्या है?",
        required=False,
        tag="hope_text",
        max_length=600,
        placeholder_en="Share your thoughts, expectations, or concerns (optional)...",
        placeholder_hi="अपने विचार, उम्मीदें या चिंताएं साझा करें (वैकल्पिक)...",
    ),
]

# 5. Perception Section (3 items)
PERCEPTION_QUESTIONS: list[InternalQuestion] = [
    InternalQuestion(
        id="guess_domain",
        type="single_choice",
        prompt_en="Which field do you think your child is most interested in?",
        prompt_hi="आपको क्या लगता है, आपका बच्चा किस क्षेत्र में सबसे ज्यादा रुचि रखता है?",
        required=True,
        tag="perception_domain",
        options=GUESS_DOMAIN_OPTIONS,
    ),
    InternalQuestion(
        id="guess_relocation",
        type="single_choice",
        prompt_en="How far do you think your child is willing to move for college or work?",
        prompt_hi="आपको क्या लगता है, आपका बच्चा कॉलेज या काम के लिए कितनी दूर जाने को तैयार है?",
        required=True,
        tag="perception_relocation",
        options=RELOCATION_OPTIONS,
    ),
    InternalQuestion(
        id="guess_risk",
        type="single_choice",
        prompt_en="How would you describe your child's appetite for career risk?",
        prompt_hi="करियर में जोखिम लेने के मामले में आपके बच्चे का रवैया कैसा है?",
        required=True,
        tag="perception_risk",
        options=[
            InternalOption("low", "Prefers safe, predictable options", "सुरक्षित और तय रास्ते पसंद करता/करती है"),
            InternalOption("medium", "Balanced: open to reasonable risks", "संतुलित: सोच-समझकर जोखिम ले सकता/सकती है"),
            InternalOption("high", "Ambitious: willing to take big risks for big rewards", "महत्वाकांक्षी: बड़े अवसरों के लिए बड़ा जोखिम लेने को तैयार"),
        ],
    ),
]

SECTIONS_ORDER: list[InternalSection] = [
    InternalSection("money", "Education Budget", "शिक्षा बजट", MONEY_QUESTIONS),
    InternalSection("risk", "Career Risk & Return", "करियर जोखिम और लाभ", RISK_QUESTIONS),
    InternalSection("plans", "Future Plans", "भविष्य की योजनाएं", PLANS_QUESTIONS),
    InternalSection("hopes", "Aspirations & Hopes", "उम्मीदें और प्राथमिकताएं", HOPES_QUESTIONS),
    InternalSection("perception", "Understanding Your Child", "बच्चे की पसंद की समझ", PERCEPTION_QUESTIONS),
]

ALL_INTAKE_QUESTIONS_MAP: dict[str, InternalQuestion] = {
    q.id: q
    for sec in SECTIONS_ORDER
    for q in sec.questions
}

QUESTION_BANK_ORDER: list[str] = [
    q.id
    for sec in SECTIONS_ORDER
    for q in sec.questions
]

REQUIRED_QUESTION_IDS: list[str] = [
    q.id
    for sec in SECTIONS_ORDER
    for q in sec.questions
    if q.required
]

TOTAL_QUESTIONS_COUNT: int = len(ALL_INTAKE_QUESTIONS_MAP)


def build_public_question(internal: InternalQuestion) -> dict[str, Any]:
    """Builds a public question dictionary copying ONLY explicit allowlist fields."""
    public_q: dict[str, Any] = {
        "id": internal.id,
        "type": internal.type,
        "prompt": {
            "en": internal.prompt_en,
            "hi": internal.prompt_hi,
        },
        "required": internal.required,
    }

    if internal.options:
        public_q["options"] = [
            {
                "id": opt.id,
                "label": {
                    "en": opt.label_en,
                    "hi": opt.label_hi,
                },
            }
            for opt in internal.options
        ]

    if internal.min is not None:
        public_q["min"] = internal.min

    if internal.max is not None:
        public_q["max"] = internal.max

    if internal.min_label_en is not None and internal.min_label_hi is not None:
        public_q["min_label"] = {
            "en": internal.min_label_en,
            "hi": internal.min_label_hi,
        }

    if internal.max_label_en is not None and internal.max_label_hi is not None:
        public_q["max_label"] = {
            "en": internal.max_label_en,
            "hi": internal.max_label_hi,
        }

    if internal.max_length is not None:
        public_q["max_length"] = internal.max_length

    if internal.placeholder_en is not None and internal.placeholder_hi is not None:
        public_q["placeholder"] = {
            "en": internal.placeholder_en,
            "hi": internal.placeholder_hi,
        }

    if internal.max_select is not None:
        public_q["max_select"] = internal.max_select

    # Strict assertion that only allowed keys are present
    assert set(public_q.keys()).issubset(PUBLIC_QUESTION_ALLOWED_KEYS)
    return public_q


def get_public_sections() -> list[dict[str, Any]]:
    """Returns all sections formatted for public API response."""
    result = []
    for sec in SECTIONS_ORDER:
        result.append({
            "id": sec.id,
            "title": {
                "en": sec.title_en,
                "hi": sec.title_hi,
            },
            "questions": [build_public_question(q) for q in sec.questions],
        })
    return result
