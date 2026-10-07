# Hardcoded stand-in for the ML question generator.

from dataclasses import dataclass, field
from typing import Any, Optional

from app.shared_questions import (
    CAREER_DOMAINS,
    InternalOption,
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
    # Hidden fields (never exposed in public responses)
    tag: Optional[str] = None
    dimension: Optional[str] = None
    correct_option_id: Optional[str] = None


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

# 1. Background Section
BACKGROUND_QUESTIONS: list[InternalQuestion] = [
    InternalQuestion(
        id="bg_stream",
        type="single_choice",
        prompt_en="Which academic stream are you studying or planning to choose?",
        prompt_hi="आप कौन सी पढ़ाई (स्ट्रीम) कर रहे हैं या चुनने की सोच रहे हैं?",
        required=True,
        options=[
            InternalOption("science_maths", "Science (with Maths / PCM)", "साइंस (गणित के साथ / PCM)"),
            InternalOption("science_bio", "Science (with Biology / PCB)", "साइंस (बायोलॉजी के साथ / PCB)"),
            InternalOption("commerce", "Commerce", "कॉमर्स"),
            InternalOption("arts", "Arts / Humanities", "आर्ट्स / मानविकी"),
            InternalOption("vocational", "Vocational / Applied Skills", "व्यावसायिक / कौशल आधारित"),
            InternalOption("undecided", "Undecided / Not sure yet", "अभी तय नहीं किया"),
        ],
    ),
    InternalQuestion(
        id="bg_marks_band",
        type="single_choice",
        prompt_en="What is your typical score range in recent exams?",
        prompt_hi="हाल की परीक्षाओं में आपके आम तौर पर कितने अंक आते हैं?",
        required=True,
        options=[
            InternalOption("below_50", "Below 50%", "50% से कम"),
            InternalOption("50_60", "50% to 60%", "50% से 60%"),
            InternalOption("60_75", "60% to 75%", "60% से 75%"),
            InternalOption("75_90", "75% to 90%", "75% से 90%"),
            InternalOption("above_90", "Above 90%", "90% से ऊपर"),
            InternalOption("not_yet", "Results not out yet", "नतीजे अभी नहीं आए हैं"),
        ],
    ),
    InternalQuestion(
        id="bg_district",
        type="text",
        prompt_en="Which district and state do you live in?",
        prompt_hi="आप किस जिले और राज्य में रहते हैं?",
        required=True,
        max_length=60,
        placeholder_en="e.g., Jaipur, Rajasthan",
        placeholder_hi="जैसे, जयपुर, राजस्थान",
    ),
    InternalQuestion(
        id="bg_languages",
        type="multi_choice",
        prompt_en="Which languages are you comfortable speaking or writing in?",
        prompt_hi="आप किन भाषाओं में बात करने या लिखने में सहज हैं?",
        required=True,
        options=[
            InternalOption("english", "English", "अंग्रेज़ी"),
            InternalOption("hindi", "Hindi", "हिंदी"),
            InternalOption("tamil", "Tamil", "तमिल"),
            InternalOption("telugu", "Telugu", "तेलुगु"),
            InternalOption("kannada", "Kannada", "कन्नड़"),
            InternalOption("malayalam", "Malayalam", "मलयालम"),
            InternalOption("other", "Other", "अन्य"),
        ],
    ),
]

# 2. Interests Section (12 items across 6 dimensions R, I, A, S, E, C, non-adjacent)
INTEREST_QUESTIONS: list[InternalQuestion] = [
    InternalQuestion(
        id="int_01",
        type="scale",
        prompt_en="How much would you enjoy fixing broken devices or building things with tools?",
        prompt_hi="टूटे उपकरणों को सुधारना या औजारों से नई चीजें बनाना आपको कितना पसंद आएगा?",
        required=True,
        min=1,
        max=5,
        min_label_en="Would not enjoy it",
        min_label_hi="बिल्कुल पसंद नहीं आएगा",
        max_label_en="Would enjoy it a lot",
        max_label_hi="बहुत पसंद आएगा",
        dimension="R",
    ),
    InternalQuestion(
        id="int_02",
        type="scale",
        prompt_en="How much would you enjoy researching why things happen in science or nature?",
        prompt_hi="विज्ञान या प्रकृति में कोई चीज़ क्यों होती है, यह खोजना आपको कितना पसंद आएगा?",
        required=True,
        min=1,
        max=5,
        min_label_en="Would not enjoy it",
        min_label_hi="बिल्कुल पसंद नहीं आएगा",
        max_label_en="Would enjoy it a lot",
        max_label_hi="बहुत पसंद आएगा",
        dimension="I",
    ),
    InternalQuestion(
        id="int_03",
        type="scale",
        prompt_en="How much would you enjoy writing creative stories or sketching illustrations?",
        prompt_hi="कहानियां लिखना या चित्र बनाना आपको कितना पसंद आएगा?",
        required=True,
        min=1,
        max=5,
        min_label_en="Would not enjoy it",
        min_label_hi="बिल्कुल पसंद नहीं आएगा",
        max_label_en="Would enjoy it a lot",
        max_label_hi="बहुत पसंद आएगा",
        dimension="A",
    ),
    InternalQuestion(
        id="int_04",
        type="scale",
        prompt_en="How much would you enjoy teaching a school subject to a younger student?",
        prompt_hi="किसी छोटे बच्चे को कोई विषय पढ़ाना या समझाना आपको कितना पसंद आएगा?",
        required=True,
        min=1,
        max=5,
        min_label_en="Would not enjoy it",
        min_label_hi="बिल्कुल पसंद नहीं आएगा",
        max_label_en="Would enjoy it a lot",
        max_label_hi="बहुत पसंद आएगा",
        dimension="S",
    ),
    InternalQuestion(
        id="int_05",
        type="scale",
        prompt_en="How much would you enjoy leading a group project and presenting the final plan?",
        prompt_hi="किसी ग्रुप प्रोजेक्ट का नेतृत्व करना और योजना पेश करना आपको कितना पसंद आएगा?",
        required=True,
        min=1,
        max=5,
        min_label_en="Would not enjoy it",
        min_label_hi="बिल्कुल पसंद नहीं आएगा",
        max_label_en="Would enjoy it a lot",
        max_label_hi="बहुत पसंद आएगा",
        dimension="E",
    ),
    InternalQuestion(
        id="int_06",
        type="scale",
        prompt_en="How much would you enjoy keeping expense records and monthly budgets neat and organized?",
        prompt_hi="खर्चों का हिसाब और रिकॉर्ड व्यवस्थित रखना आपको कितना पसंद आएगा?",
        required=True,
        min=1,
        max=5,
        min_label_en="Would not enjoy it",
        min_label_hi="बिल्कुल पसंद नहीं आएगा",
        max_label_en="Would enjoy it a lot",
        max_label_hi="बहुत पसंद आएगा",
        dimension="C",
    ),
    InternalQuestion(
        id="int_07",
        type="scale",
        prompt_en="How much would you enjoy assembling mechanical machinery or working out in the field?",
        prompt_hi="मशीनों के पुर्जे जोड़ना या खुले मैदान में काम करना आपको कितना पसंद आएगा?",
        required=True,
        min=1,
        max=5,
        min_label_en="Would not enjoy it",
        min_label_hi="बिल्कुल पसंद नहीं आएगा",
        max_label_en="Would enjoy it a lot",
        max_label_hi="बहुत पसंद आएगा",
        dimension="R",
    ),
    InternalQuestion(
        id="int_08",
        type="scale",
        prompt_en="How much would you enjoy setting up experiments to test your own theories?",
        prompt_hi="अपनी परिकल्पनाओं को परखने के लिए छोटे प्रयोग करना आपको कितना पसंद आएगा?",
        required=True,
        min=1,
        max=5,
        min_label_en="Would not enjoy it",
        min_label_hi="बिल्कुल पसंद नहीं आएगा",
        max_label_en="Would enjoy it a lot",
        max_label_hi="बहुत पसंद आएगा",
        dimension="I",
    ),
    InternalQuestion(
        id="int_09",
        type="scale",
        prompt_en="How much would you enjoy designing layouts, graphics, or poster visuals?",
        prompt_hi="पोस्टर, डिज़ाइन या विजुअल्स को सुंदर और आकर्षक बनाना आपको कितना पसंद आएगा?",
        required=True,
        min=1,
        max=5,
        min_label_en="Would not enjoy it",
        min_label_hi="बिल्कुल पसंद नहीं आएगा",
        max_label_en="Would enjoy it a lot",
        max_label_hi="बहुत पसंद आएगा",
        dimension="A",
    ),
    InternalQuestion(
        id="int_10",
        type="scale",
        prompt_en="How much would you enjoy listening to a friend and helping them solve a difficult problem?",
        prompt_hi="किसी दोस्त की बात सुनकर उसकी परेशानी सुलझाने में मदद करना आपको कितना पसंद आएगा?",
        required=True,
        min=1,
        max=5,
        min_label_en="Would not enjoy it",
        min_label_hi="बिल्कुल पसंद नहीं आएगा",
        max_label_en="Would enjoy it a lot",
        max_label_hi="बहुत पसंद आएगा",
        dimension="S",
    ),
    InternalQuestion(
        id="int_11",
        type="scale",
        prompt_en="How much would you enjoy pitching a new product idea and launching a small venture?",
        prompt_hi="किसी नए विचार को लोगों के सामने रखना और छोटा काम शुरू करना आपको कितना पसंद आएगा?",
        required=True,
        min=1,
        max=5,
        min_label_en="Would not enjoy it",
        min_label_hi="बिल्कुल पसंद नहीं आएगा",
        max_label_en="Would enjoy it a lot",
        max_label_hi="बहुत पसंद आएगा",
        dimension="E",
    ),
    InternalQuestion(
        id="int_12",
        type="scale",
        prompt_en="How much would you enjoy organizing lists and data neatly in a spreadsheet?",
        prompt_hi="स्प्रेडशीट में जानकारी और डेटा को करीने से व्यवस्थित करना आपको कितना पसंद आएगा?",
        required=True,
        min=1,
        max=5,
        min_label_en="Would not enjoy it",
        min_label_hi="बिल्कुल पसंद नहीं आएगा",
        max_label_en="Would enjoy it a lot",
        max_label_hi="बहुत पसंद आएगा",
        dimension="C",
    ),
]

# 3. Aptitude Section (4 original puzzles, class 10-12, correct options spread across a, b, c, d)
APTITUDE_QUESTIONS: list[InternalQuestion] = [
    # Worked check: In a 3x3x3 cube cut into 27 units, exactly 1 center cube per face has only 1 exterior face, giving 6 * 1 = 6 cubes with one painted face (option a).
    InternalQuestion(
        id="apt_spatial",
        type="single_choice",
        prompt_en="A solid cube is painted on all six outside faces and then sliced into 27 identical smaller cubes (3×3×3). How many of the smaller cubes have paint on exactly one face?",
        prompt_hi="एक ठोस घन के सभी छह बाहरी फलकों पर रंग किया जाता है और फिर उसे 27 एकसमान छोटे घनों (3×3×3) में काटा जाता है। इनमें से कितने छोटे घनों के केवल एक फलक पर रंग होगा?",
        required=True,
        options=[
            InternalOption("a", "6", "6"),
            InternalOption("b", "8", "8"),
            InternalOption("c", "10", "10"),
            InternalOption("d", "12", "12"),
        ],
        correct_option_id="a",
    ),
    # Worked check: Marked Price = 1200, SP after 25% discount = 1200 * 0.75 = 900. Since Profit = 20%, CP = 900 / 1.20 = 750 (option b).
    InternalQuestion(
        id="apt_numerical",
        type="single_choice",
        prompt_en="A merchant marks an article at ₹1,200 and offers a 25% discount. If the merchant still earns a 20% profit on the cost price, what is the cost price?",
        prompt_hi="एक व्यापारी किसी वस्तु पर ₹1,200 अंकित करता है और 25% की छूट देता है। यदि वह फिर भी लागत मूल्य पर 20% लाभ कमाता है, तो वस्तु का लागत मूल्य क्या है?",
        required=True,
        options=[
            InternalOption("a", "₹720", "₹720"),
            InternalOption("b", "₹750", "₹750"),
            InternalOption("c", "₹800", "₹800"),
            InternalOption("d", "₹840", "₹840"),
        ],
        correct_option_id="b",
    ),
    # Worked check: 'Some schools with libraries also have computer labs' directly implies those schools possess both, meaning at least some schools with computer labs have a library (option c).
    InternalQuestion(
        id="apt_verbal",
        type="single_choice",
        prompt_en="Consider the statement: 'All registered schools maintain a library. Some schools with libraries also have a computer lab.' Which conclusion must be true?",
        prompt_hi="इस कथन पर विचार करें: 'सभी पंजीकृत स्कूलों में लाइब्रेरी होती है। लाइब्रेरी वाले कुछ स्कूलों में कंप्यूटर लैब भी है।' कौन सा निष्कर्ष निश्चित रूप से सत्य है?",
        required=True,
        options=[
            InternalOption("a", "All schools with computer labs are registered.", "कंप्यूटर लैब वाले सभी स्कूल पंजीकृत हैं।"),
            InternalOption("b", "Every registered school has a computer lab.", "प्रत्येक पंजीकृत स्कूल में कंप्यूटर लैब है।"),
            InternalOption("c", "At least some schools with computer labs have a library.", "कंप्यूटर लैब वाले कम से कम कुछ स्कूलों में लाइब्रेरी है।"),
            InternalOption("d", "No registered school lacks a computer lab.", "किसी भी पंजीकृत स्कूल में कंप्यूटर लैब की कमी नहीं है।"),
        ],
        correct_option_id="c",
    ),
    # Worked check: Ranking is Bina > Chetan > Kamal > Deepa > Arun; Arun is in last place (option d).
    InternalQuestion(
        id="apt_logical",
        type="single_choice",
        prompt_en="In a 100m race with five runners: Bina finished ahead of Kamal. Chetan finished between Bina and Kamal. Kamal finished ahead of Deepa, and Arun finished behind Deepa. Who finished in last place?",
        prompt_hi="पाँच धावकों की दौड़ में: बीना कमल से आगे रही। चेतन बीना और कमल के बीच में रहा। कमल दीपा से आगे रहा, और अरुण दीपा से पीछे रहा। दौड़ में सबसे आखिरी स्थान पर कौन रहा?",
        required=True,
        options=[
            InternalOption("a", "Deepa", "दीपा"),
            InternalOption("b", "Kamal", "कमल"),
            InternalOption("c", "Chetan", "चेतन"),
            InternalOption("d", "Arun", "अरुण"),
        ],
        correct_option_id="d",
    ),
]

# 4. Values Section (5 items)
VALUES_QUESTIONS: list[InternalQuestion] = [
    InternalQuestion(
        id="val_security",
        type="slider",
        prompt_en="How much does job security and steady income matter to you in a career?",
        prompt_hi="करियर में नौकरी की सुरक्षा और नियमित आय आपके लिए कितनी महत्वपूर्ण है?",
        required=True,
        min=0,
        max=10,
        min_label_en="Not important",
        min_label_hi="महत्वपूर्ण नहीं",
        max_label_en="Extremely important",
        max_label_hi="बेहद महत्वपूर्ण",
    ),
    InternalQuestion(
        id="val_independence",
        type="slider",
        prompt_en="How much does having the freedom to work independently matter to you in a career?",
        prompt_hi="करियर में अपनी मर्जी और स्वतंत्रता से काम करना आपके लिए कितना महत्वपूर्ण है?",
        required=True,
        min=0,
        max=10,
        min_label_en="Not important",
        min_label_hi="महत्वपूर्ण नहीं",
        max_label_en="Extremely important",
        max_label_hi="बेहद महत्वपूर्ण",
    ),
    InternalQuestion(
        id="val_helping",
        type="slider",
        prompt_en="How much does making a positive difference to society matter to you in a career?",
        prompt_hi="करियर में समाज और लोगों की भलाई के लिए काम करना आपके लिए कितना महत्वपूर्ण है?",
        required=True,
        min=0,
        max=10,
        min_label_en="Not important",
        min_label_hi="महत्वपूर्ण नहीं",
        max_label_en="Extremely important",
        max_label_hi="बेहद महत्वपूर्ण",
    ),
    InternalQuestion(
        id="val_income",
        type="slider",
        prompt_en="How much does high earning potential and financial growth matter to you in a career?",
        prompt_hi="करियर में अधिक कमाई और आर्थिक तरक्की आपके लिए कितनी महत्वपूर्ण है?",
        required=True,
        min=0,
        max=10,
        min_label_en="Not important",
        min_label_hi="महत्वपूर्ण नहीं",
        max_label_en="Extremely important",
        max_label_hi="बेहद महत्वपूर्ण",
    ),
    InternalQuestion(
        id="val_creativity",
        type="slider",
        prompt_en="How much does the chance to express new ideas and be creative matter to you in a career?",
        prompt_hi="करियर में नए विचार आजमाने और रचनात्मक होने का अवसर आपके लिए कितना महत्वपूर्ण है?",
        required=True,
        min=0,
        max=10,
        min_label_en="Not important",
        min_label_hi="महत्वपूर्ण नहीं",
        max_label_en="Extremely important",
        max_label_hi="बेहद महत्वपूर्ण",
    ),
]

# 5. Preferences Section (6 items, all required: pref_risk_1..3, pref_relocation, pref_time_to_earn, pref_domain_wish)
PREFERENCES_QUESTIONS: list[InternalQuestion] = [
    InternalQuestion(
        id="pref_risk_1",
        type="single_choice",
        prompt_en="Imagine two starting job offers after college. Which would you choose?",
        prompt_hi="मान लें कि कॉलेज के बाद आपके सामने नौकरी के दो विकल्प हैं। आप किसे चुनेंगे?",
        required=True,
        tag="risk",
        options=RISK_1_OPTIONS,
    ),
    InternalQuestion(
        id="pref_risk_2",
        type="single_choice",
        prompt_en="Imagine a different set of starting job offers. Which would you choose?",
        prompt_hi="अब मान लें कि आपके सामने ये दो विकल्प हैं। आप किसे चुनेंगे?",
        required=True,
        tag="risk",
        options=RISK_2_OPTIONS,
    ),
    InternalQuestion(
        id="pref_risk_3",
        type="single_choice",
        prompt_en="Imagine a higher guaranteed offer vs the same variable opportunity. Which would you choose?",
        prompt_hi="मान लें कि एक अधिक सुरक्षित विकल्प और वही अनिश्चित अवसर सामने है। आप क्या चुनेंगे?",
        required=True,
        tag="risk",
        options=RISK_3_OPTIONS,
    ),
    InternalQuestion(
        id="pref_relocation",
        type="single_choice",
        prompt_en="How far are you comfortable moving for higher studies or work?",
        prompt_hi="पढ़ाई या नौकरी के लिए आप कितनी दूर जाने में सहज हैं?",
        required=True,
        tag="relocation",
        options=RELOCATION_OPTIONS,
    ),
    InternalQuestion(
        id="pref_time_to_earn",
        type="single_choice",
        prompt_en="How soon do you expect to start earning after completing school?",
        prompt_hi="स्कूल पूरा करने के बाद आप कब तक कमाई शुरू करने की उम्मीद करते हैं?",
        required=True,
        tag="time_to_earn",
        options=TIME_TO_EARN_OPTIONS,
    ),
    InternalQuestion(
        id="pref_domain_wish",
        type="multi_choice",
        prompt_en="Which career domains are you most interested in exploring? (Select up to 3)",
        prompt_hi="आप किन क्षेत्रों में करियर बनाने के लिए सबसे अधिक उत्सुक हैं? (अधिकतम 3 चुनें)",
        required=True,
        tag="domain_wish",
        max_select=3,
        options=CAREER_DOMAINS,
    ),
]

# 6. Free Text Section (1 item)
FREE_TEXT_QUESTIONS: list[InternalQuestion] = [
    InternalQuestion(
        id="free_text_1",
        type="long_text",
        prompt_en="What do you do for fun? What problem around you would you like to fix?",
        prompt_hi="आप खाली समय में क्या करना पसंद करते हैं? अपने आस-पास की कौन सी समस्या को आप हल करना चाहेंगे?",
        required=False,
        max_length=600,
        placeholder_en="Share your hobbies or issues you care about (optional)...",
        placeholder_hi="अपने शौक या ऐसे मुद्दे साझा करें जिनकी आप परवाह करते हैं (वैकल्पिक)...",
    ),
]

SECTIONS_ORDER: list[InternalSection] = [
    InternalSection("background", "Background", "पृष्ठभूमि", BACKGROUND_QUESTIONS),
    InternalSection("interests", "Interests", "रुचियां", INTEREST_QUESTIONS),
    InternalSection("aptitude", "Aptitude", "योग्यता", APTITUDE_QUESTIONS),
    InternalSection("values", "Values", "कार्य मूल्य", VALUES_QUESTIONS),
    InternalSection("preferences", "Preferences", "प्राथमिकताएं", PREFERENCES_QUESTIONS),
    InternalSection("free_text", "Free Text", "आपकी राय", FREE_TEXT_QUESTIONS),
]

# Flat lookup of all internal questions
ALL_QUESTIONS_MAP: dict[str, InternalQuestion] = {
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

TOTAL_QUESTIONS_COUNT: int = len(ALL_QUESTIONS_MAP)


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


# ---------------------------------------------------------------------------
# Internal Scoring & Bridge Extraction Helpers (Never exposed in public API)
# ---------------------------------------------------------------------------
APTITUDE_KEY_MAP: dict[str, str] = {
    "numerical": "apt_numerical",
    "verbal": "apt_verbal",
    "spatial": "apt_spatial",
    "logical": "apt_logical",
}


def score_aptitude_answers(answers: dict[str, Any]) -> dict[str, bool]:
    """Score stored student aptitude answers against hidden correct option IDs.

    Returns {numerical, verbal, spatial, logical} booleans using the hidden answer key.
    Internal function; never returned by any endpoint.
    """
    answers = answers or {}
    scored: dict[str, bool] = {}
    for trait, q_id in APTITUDE_KEY_MAP.items():
        q = ALL_QUESTIONS_MAP.get(q_id)
        if q is not None and q.correct_option_id is not None:
            user_choice = answers.get(q_id)
            scored[trait] = bool(user_choice and str(user_choice).strip() == q.correct_option_id)
        else:
            scored[trait] = False
    return scored


def get_interest_item_to_dimension() -> dict[str, str]:
    """Extract item-to-dimension mapping from hidden interest question attributes."""
    return {
        q.id: q.dimension
        for q in INTEREST_QUESTIONS
        if q.dimension is not None
    }

