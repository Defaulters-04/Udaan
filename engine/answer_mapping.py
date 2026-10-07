"""Pure answer mapping functions for the PRISM Engine.

Converts front-facing Udaan assessment and intake answer dictionaries directly into
strongly-typed Student and ParentProfile domain models with zero I/O and zero HTTP.
All financial bands and uncollected defaults use explicit, deterministic assumptions.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List, Set, Union

from engine.domains import (
    get_canonical_domain_ids,
    normalize_category_to_domain_id,
)
from engine.student_fit.models import Student, AcademicProfile
from engine.parent.models import ParentProfile, SectorRatings


# ---------------------------------------------------------------------------
# Default Item-to-Dimension Mapping for RIASEC Interests (int_01 .. int_12)
# ---------------------------------------------------------------------------
DEFAULT_ITEM_TO_DIMENSION: Dict[str, str] = {
    "int_01": "R",
    "int_02": "R",
    "int_03": "I",
    "int_04": "I",
    "int_05": "A",
    "int_06": "A",
    "int_07": "S",
    "int_08": "S",
    "int_09": "E",
    "int_10": "E",
    "int_11": "C",
    "int_12": "C",
}

# ---------------------------------------------------------------------------
# Stream to Academic Subjects Mapping
# ---------------------------------------------------------------------------
STREAM_SUBJECTS_MAP: Dict[str, Set[str]] = {
    "science_maths": {"physics", "chemistry", "mathematics", "english"},
    "science_bio": {"physics", "chemistry", "biology", "english"},
    "commerce": {"commerce", "accountancy", "economics", "business_studies", "mathematics", "english"},
    "arts": {"history", "political_science", "geography", "sociology", "psychology", "english"},
    "vocational": {"vocational", "applied_arts", "information_technology", "english"},
    "undecided": {
        "physics",
        "chemistry",
        "mathematics",
        "biology",
        "commerce",
        "accountancy",
        "economics",
        "business_studies",
        "history",
        "political_science",
        "geography",
        "english",
    },
}

# ---------------------------------------------------------------------------
# Marks Band to Percentage Conversion (Midpoint Rule)
# ---------------------------------------------------------------------------
MARKS_BAND_MAP: Dict[str, float] = {
    "below_50": 45.0,     # Assumed midpoint [40, 50]
    "50_60": 55.0,        # Assumed midpoint [50, 60]
    "60_75": 67.5,        # Assumed midpoint [60, 75]
    "75_90": 82.5,        # Assumed midpoint [75, 90]
    "above_90": 95.0,     # Assumed midpoint [90, 100]
    "not_yet": 100.0,     # Assumed default: unknown/unverified, passes academic cutoffs without blocking
}

# Uncollected qualifying exams default (all pass-through so academic gate never blocks on uncollected data)
ALL_QUALIFYING_EXAMS_DEFAULT: Set[str] = {
    "jee",
    "neet",
    "clat",
    "cat",
    "gate",
    "cuet",
    "nda",
    "nift",
    "nid",
    "uceed",
    "ceed",
    "nata",
}

# ---------------------------------------------------------------------------
# Relocation Mapping (Identical for Student & Parent)
# ---------------------------------------------------------------------------
RELOCATION_MAP: Dict[str, float] = {
    "home_city": 0.0,
    "same_state": 0.33,
    "anywhere_india": 0.67,
    "abroad_ok": 1.0,
}

# ---------------------------------------------------------------------------
# Time to Earn Horizon Mapping (Years, Identical for Student & Parent)
# ---------------------------------------------------------------------------
TIME_TO_EARN_MAP: Dict[str, float] = {
    "within_4y": 4.0,
    "five_six": 6.0,
    "seven_plus": 8.0,
}

# ---------------------------------------------------------------------------
# Parent Financial Bands to INR (Midpoint Rule with stated top-band rule)
# ---------------------------------------------------------------------------
# Income Band: Yearly rupees converted to monthly (M_inc = yearly / 12)
YEARLY_INCOME_BAND_MAP: Dict[str, float] = {
    "under_3l": 150000.0,    # Assumed midpoint [0, 3L] -> monthly 12,500
    "3_6l": 450000.0,        # Assumed midpoint [3L, 6L] -> monthly 37,500
    "6_12l": 900000.0,       # Assumed midpoint [6L, 12L] -> monthly 75,000
    "12_25l": 1850000.0,     # Assumed midpoint [12L, 25L] -> monthly 154,167
    "over_25l": 3500000.0,   # Assumed 1.4x lower bound (>25L) -> monthly 291,667
}

# Liquid Savings Band (S) in INR
SAVINGS_BAND_MAP: Dict[str, float] = {
    "none": 0.0,             # Assumed exactly 0
    "under_1l": 50000.0,     # Assumed midpoint [0, 1L]
    "1_3l": 200000.0,        # Assumed midpoint [1L, 3L]
    "3_8l": 550000.0,        # Assumed midpoint [3L, 8L]
    "over_8l": 1200000.0,    # Assumed 1.5x lower bound (>8L)
}

# Maximum Loan Capacity Band (L_max) in INR
LOAN_BAND_MAP: Dict[str, float] = {
    "none": 0.0,             # Assumed exactly 0
    "up_to_3l": 150000.0,    # Assumed midpoint [0, 3L]
    "3_8l": 550000.0,        # Assumed midpoint [3L, 8L]
    "8_15l": 1150000.0,      # Assumed midpoint [8L, 15L]
    "over_15l": 2000000.0,   # Assumed 1.33x lower bound (>15L)
}

# Monthly Surplus Band (M) in INR
MONTHLY_SURPLUS_BAND_MAP: Dict[str, float] = {
    "none": 0.0,             # Assumed exactly 0
    "under_5k": 2500.0,      # Assumed midpoint [0, 5k]
    "5k_15k": 10000.0,       # Assumed midpoint [5k, 15k]
    "15k_30k": 22500.0,      # Assumed midpoint [15k, 30k]
    "over_30k": 45000.0,     # Assumed 1.5x lower bound (>30k)
}

# Monthly Existing EMI Band (E_exist) in INR
MONTHLY_EMI_BAND_MAP: Dict[str, float] = {
    "none": 0.0,             # Assumed exactly 0
    "under_5k": 2500.0,      # Assumed midpoint [0, 5k]
    "5k_15k": 10000.0,       # Assumed midpoint [5k, 15k]
    "over_15k": 20000.0,     # Assumed 1.33x lower bound (>15k)
}


# ---------------------------------------------------------------------------
# Helper: Risk Computation (Number of 'gamble' choices / 3.0)
# ---------------------------------------------------------------------------
def compute_risk_tolerance(r1: Any, r2: Any, r3: Any) -> float:
    """Compute risk score from 3 binary choices (0.0, 0.33, 0.67, 1.0).

    safe pays guaranteed return; gamble takes the 50/50 risk.
    """
    choices = [str(r1 or "").strip().lower(), str(r2 or "").strip().lower(), str(r3 or "").strip().lower()]
    gamble_count = sum(1 for c in choices if c == "gamble")
    return round(gamble_count / 3.0, 2)


# ---------------------------------------------------------------------------
# Helper: Domain Scoring (1-to-5 scale: Picked = 5.0, Not Picked = 1.0)
# ---------------------------------------------------------------------------
def compute_domain_ratings(raw_wishes: Union[List[str], str, None]) -> Dict[str, float]:
    """Score all 7 canonical domains on 1-5 scale.

    Picked domains receive 5.0, unpicked receive 1.0 so unpicked domains
    are not erroneously treated as neutral 3.0.
    """
    if raw_wishes is None:
        picked_set = set()
    elif isinstance(raw_wishes, str):
        picked_set = {normalize_category_to_domain_id(raw_wishes)}
    elif isinstance(raw_wishes, (list, tuple, set)):
        picked_set = {normalize_category_to_domain_id(str(d)) for d in raw_wishes if d}
    else:
        picked_set = set()

    canonical_ids = get_canonical_domain_ids()
    ratings: Dict[str, float] = {}
    for dom_id in canonical_ids:
        ratings[dom_id] = 5.0 if dom_id in picked_set else 1.0

    return ratings


# ---------------------------------------------------------------------------
# Pure Student Profile Builder
# ---------------------------------------------------------------------------
def student_from_answers(
    answers: Dict[str, Any],
    aptitude_correct: Optional[Dict[str, bool]] = None,
    item_to_dimension: Optional[Dict[str, str]] = None,
    stage: str = "school",
    student_id: str = "student",
) -> Student:
    """Pure function mapping front-facing student questionnaire answers to Student domain model.

    No I/O, no HTTP, pure determinism.
    """
    answers = answers or {}
    aptitude_correct = aptitude_correct or {}
    dim_map = item_to_dimension or DEFAULT_ITEM_TO_DIMENSION

    # 1. RIASEC Interest dimensions: mean of mapped items (x - 1) / 4.0 in [0, 1]
    dim_values: Dict[str, List[float]] = {d: [] for d in ("R", "I", "A", "S", "E", "C")}
    for item_id, dim in dim_map.items():
        if dim in dim_values and item_id in answers:
            try:
                raw_val = float(answers[item_id])
                clamped = max(1.0, min(5.0, raw_val))
                normalized = (clamped - 1.0) / 4.0
                dim_values[dim].append(normalized)
            except (ValueError, TypeError):
                pass

    I_s: Dict[str, float] = {}
    for dim, vals in dim_values.items():
        if vals:
            I_s[dim] = round(sum(vals) / len(vals), 4)
        else:
            I_s[dim] = 0.50  # Neutral default if dimension items omitted

    # 2. Aptitude: 1.0 if correct (True), 0.0 if incorrect (False), 0.5 if omitted
    apt_dimensions = ["logical", "numerical", "verbal", "spatial"]
    a_j: Dict[str, float] = {}
    for trait in apt_dimensions:
        if trait in aptitude_correct:
            a_j[trait] = 1.0 if bool(aptitude_correct[trait]) else 0.0
        elif trait in answers:
            # Fallback if passed directly in answers dict
            val = answers[trait]
            a_j[trait] = 1.0 if bool(val) else 0.0
        else:
            a_j[trait] = 0.50  # Assumed neutral default if unmeasured

    # 3. Academics Profile
    stream = str(answers.get("bg_stream", "undecided")).strip().lower()
    subjects = STREAM_SUBJECTS_MAP.get(stream, STREAM_SUBJECTS_MAP["undecided"])

    marks_band = str(answers.get("bg_marks_band", "not_yet")).strip().lower()
    marks = MARKS_BAND_MAP.get(marks_band, 100.0)

    academics = AcademicProfile(
        marks=marks,
        subjects=subjects,
        exams=set(ALL_QUALIFYING_EXAMS_DEFAULT),  # Assumed default unverified exams
    )

    # 4. Values mapped to Big Five Personality Traits P_j (scaled 0-1)
    # Assumed defaults: 0.5 neutral baseline, updated by user values if present
    openness = float(answers.get("val_creativity", 5.0)) / 10.0 if "val_creativity" in answers else 0.50
    conscientiousness = float(answers.get("val_security", 5.0)) / 10.0 if "val_security" in answers else 0.50
    agreeableness = float(answers.get("val_helping", 5.0)) / 10.0 if "val_helping" in answers else 0.50
    extraversion = float(answers.get("val_independence", 5.0)) / 10.0 if "val_independence" in answers else 0.50
    neuroticism = 0.50  # Assumed neutral default

    P_j = {
        "openness": max(0.0, min(1.0, openness)),
        "conscientiousness": max(0.0, min(1.0, conscientiousness)),
        "agreeableness": max(0.0, min(1.0, agreeableness)),
        "extraversion": max(0.0, min(1.0, extraversion)),
        "neuroticism": neuroticism,
    }

    # 5. Shared Dimensions with Parent Profile
    # Risk
    r1 = answers.get("pref_risk_1")
    r2 = answers.get("pref_risk_2")
    r3 = answers.get("pref_risk_3")
    risk_appetite = compute_risk_tolerance(r1, r2, r3)

    # Relocation
    reloc_key = str(answers.get("pref_relocation", "home_city")).strip().lower()
    relocation_willingness = RELOCATION_MAP.get(reloc_key, 0.50)

    # Time to income
    time_key = str(answers.get("pref_time_to_earn", "within_4y")).strip().lower()
    max_years_to_income = TIME_TO_EARN_MAP.get(time_key, 4.0)

    # Domain preferences (1-5 scale)
    domain_wish = answers.get("pref_domain_wish")
    domain_preference = compute_domain_ratings(domain_wish)

    return Student(
        student_id=str(student_id or "student"),
        stage=stage if stage in {"school", "college"} else "school",
        I_s=I_s,
        a_j=a_j,
        P_k={},  # Skills uncollected: empty dict (assumed default, does not penalize)
        P_j=P_j,
        academics=academics,
        risk_appetite=risk_appetite,
        domain_preference=domain_preference,
        relocation_willingness=relocation_willingness,
        max_years_to_income=max_years_to_income,
    )


# ---------------------------------------------------------------------------
# Pure Parent Profile Builder
# ---------------------------------------------------------------------------
def parent_from_answers(answers: Dict[str, Any]) -> ParentProfile:
    """Pure function mapping front-facing parent questionnaire answers to ParentProfile domain model.

    No I/O, no HTTP, pure determinism.
    """
    answers = answers or {}

    # 1. Financial balance sheet
    # Gross yearly household income converted to gross monthly household income (M_inc)
    income_band = str(answers.get("income_band", "3_6l")).strip().lower()
    yearly_income = YEARLY_INCOME_BAND_MAP.get(income_band, 450000.0)
    household_income = round(yearly_income / 12.0, 2)

    # Total liquid savings (S)
    savings_band = str(answers.get("savings_band", "under_1l")).strip().lower()
    savings = SAVINGS_BAND_MAP.get(savings_band, 50000.0)

    # Maximum educational loan willingness/capacity (L_max)
    loan_band = str(answers.get("loan_band", "up_to_3l")).strip().lower()
    loan_max = LOAN_BAND_MAP.get(loan_band, 150000.0)

    # Monthly uncommitted disposable cashflow / surplus (M)
    surplus_band = str(answers.get("surplus_band", "under_5k")).strip().lower()
    monthly_surplus = MONTHLY_SURPLUS_BAND_MAP.get(surplus_band, 2500.0)

    # Existing monthly EMI commitments (E_exist)
    emi_band = str(answers.get("emi_band", "none")).strip().lower()
    existing_emis = MONTHLY_EMI_BAND_MAP.get(emi_band, 0.0)

    # 2. Risk Appetite (R_p)
    r1 = answers.get("risk_1")
    r2 = answers.get("risk_2")
    r3 = answers.get("risk_3")
    risk = compute_risk_tolerance(r1, r2, r3)

    # 3. Relocation Willingness (rho_p)
    reloc_key = str(answers.get("relocation", "home_city")).strip().lower()
    relocation_willingness = RELOCATION_MAP.get(reloc_key, 0.50)

    # 4. Maximum Years to First Income (T_p)
    time_key = str(answers.get("time_to_earn", "within_4y")).strip().lower()
    max_years_to_income = TIME_TO_EARN_MAP.get(time_key, 4.0)

    # 5. Career Domain Ratings (1-5 scale)
    domain_wish = answers.get("domain_wish")
    domain_ratings = compute_domain_ratings(domain_wish)

    # 6. Uncollected Neutral Defaults (guaranteed not to block or unfairly penalize)
    min_salary = 300000.0  # Assumed default: modest INR 3 LPA baseline
    sector_ratings = SectorRatings(govt=3, private=3, entrepreneurship=3)  # Assumed neutral
    dependents = 1  # Assumed default: 1 child

    return ParentProfile(
        savings=savings,
        monthly_surplus=monthly_surplus,
        household_income=household_income,
        existing_emis=existing_emis,
        loan_max=loan_max,
        domain_ratings=domain_ratings,
        sector_ratings=sector_ratings,
        min_salary=min_salary,
        max_years_to_income=max_years_to_income,
        relocation_willingness=relocation_willingness,
        risk=risk,
        dependents=dependents,
    )
