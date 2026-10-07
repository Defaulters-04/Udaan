"""Tests for engine answer mapping and public facade."""

import pytest
from engine.answer_mapping import (
    student_from_answers,
    parent_from_answers,
    compute_risk_tolerance,
    compute_domain_ratings,
    STREAM_SUBJECTS_MAP,
    MARKS_BAND_MAP,
    YEARLY_INCOME_BAND_MAP,
    SAVINGS_BAND_MAP,
    LOAN_BAND_MAP,
    MONTHLY_SURPLUS_BAND_MAP,
    MONTHLY_EMI_BAND_MAP,
)
from engine.domains import get_canonical_domain_ids
from engine.public import overall_conflict, per_career_scores, negotiate, unified_roadmap


# ---------------------------------------------------------------------------
# Risk Mapping Tests
# ---------------------------------------------------------------------------
def test_risk_all_safe_and_all_gamble():
    """Verify risk mapping: count(gamble)/3 = 0.0, 0.33, 0.67, 1.0."""
    assert compute_risk_tolerance("safe", "safe", "safe") == 0.0
    assert compute_risk_tolerance("gamble", "safe", "safe") == 0.33
    assert compute_risk_tolerance("safe", "gamble", "safe") == 0.33
    assert compute_risk_tolerance("gamble", "gamble", "safe") == 0.67
    assert compute_risk_tolerance("gamble", "gamble", "gamble") == 1.0
    # Case insensitivity & whitespace
    assert compute_risk_tolerance(" Gamble ", "SAFE", "gamble") == 0.67


# ---------------------------------------------------------------------------
# Domain Scoring Rule Tests
# ---------------------------------------------------------------------------
def test_domain_scoring_rule():
    """Verify domain scoring rule: picked = 5.0, unpicked = 1.0 (never 3.0)."""
    canonical_ids = get_canonical_domain_ids()
    assert len(canonical_ids) == 7

    picked = ["tech_engineering", "healthcare_medicine"]
    ratings = compute_domain_ratings(picked)

    assert len(ratings) == 7
    assert ratings["tech_engineering"] == 5.0
    assert ratings["healthcare_medicine"] == 5.0
    assert ratings["business_management"] == 1.0
    assert ratings["design_creative"] == 1.0
    assert ratings["media_entertainment"] == 1.0
    assert ratings["humanities_law"] == 1.0
    assert ratings["sciences"] == 1.0

    # Ensure unpicked never defaults to neutral 3.0
    assert 3.0 not in ratings.values()


def test_domain_scoring_with_raw_labels():
    """Verify domain scoring handles raw category labels by normalizing to canonical IDs."""
    ratings = compute_domain_ratings(["Technology & Engineering", "Management"])
    assert ratings["tech_engineering"] == 5.0
    assert ratings["business_management"] == 5.0
    assert ratings["sciences"] == 1.0


# ---------------------------------------------------------------------------
# Student Answer Mapping Tests
# ---------------------------------------------------------------------------
def test_student_from_answers_comprehensive():
    """Verify student_from_answers maps all assessment fields properly."""
    answers = {
        "bg_stream": "science_maths",
        "bg_marks_band": "75_90",
        "int_01": 5, "int_02": 4,  # R -> mean ((1.0 + 0.75)/2) = 0.875
        "int_03": 5, "int_04": 5,  # I -> 1.0
        "int_05": 1, "int_06": 1,  # A -> 0.0
        "int_07": 3, "int_08": 3,  # S -> 0.5
        "int_09": 3, "int_10": 3,  # E -> 0.5
        "int_11": 4, "int_12": 4,  # C -> 0.75
        "val_security": 8,
        "val_independence": 6,
        "val_helping": 4,
        "val_income": 9,
        "val_creativity": 7,
        "pref_risk_1": "gamble",
        "pref_risk_2": "safe",
        "pref_risk_3": "gamble",
        "pref_relocation": "anywhere_india",
        "pref_time_to_earn": "within_4y",
        "pref_domain_wish": ["tech_engineering"],
    }
    aptitude_correct = {
        "numerical": True,
        "verbal": False,
        "spatial": True,
        "logical": True,
    }

    student = student_from_answers(answers, aptitude_correct)

    assert student.student_id == "student"
    assert student.academics.marks == 82.5  # Midpoint of 75_90
    assert "physics" in student.academics.subjects
    assert "mathematics" in student.academics.subjects

    # Aptitude
    assert student.a_j["numerical"] == 1.0
    assert student.a_j["verbal"] == 0.0
    assert student.a_j["spatial"] == 1.0
    assert student.a_j["logical"] == 1.0

    # RIASEC
    assert student.I_s["R"] == pytest.approx(0.875, abs=0.01)
    assert student.I_s["I"] == 1.0
    assert student.I_s["A"] == 0.0

    # Shared dimensions
    assert student.risk_appetite == 0.67  # 2 gambles / 3
    assert student.relocation_willingness == 0.67  # anywhere_india
    assert student.max_years_to_income == 4.0
    assert student.domain_preference["tech_engineering"] == 5.0
    assert student.domain_preference["business_management"] == 1.0


def test_unknown_marks_not_yet_does_not_block():
    """Verify marks 'not_yet' sets marks to 100% and does not block."""
    answers = {
        "bg_stream": "undecided",
        "bg_marks_band": "not_yet",
        "pref_risk_1": "safe",
        "pref_risk_2": "safe",
        "pref_risk_3": "safe",
    }
    student = student_from_answers(answers)
    assert student.academics.marks == 100.0  # Assumed default
    assert "mathematics" in student.academics.subjects
    assert "physics" in student.academics.subjects
    assert "biology" in student.academics.subjects
    # All exams assumed present so student is never blocked
    assert len(student.academics.exams) > 0


# ---------------------------------------------------------------------------
# Parent Answer Mapping Tests
# ---------------------------------------------------------------------------
def test_parent_from_answers_comprehensive():
    """Verify parent_from_answers maps all financial bands, risk, and preferences."""
    answers = {
        "income_band": "6_12l",
        "savings_band": "3_8l",
        "loan_band": "8_15l",
        "surplus_band": "15k_30k",
        "emi_band": "5k_15k",
        "risk_1": "safe",
        "risk_2": "safe",
        "risk_3": "safe",
        "relocation": "home_city",
        "time_to_earn": "five_six",
        "domain_wish": ["business_management"],
    }
    parent = parent_from_answers(answers)

    # Financial conversions
    # 6_12l yearly = 900,000 / 12 = 75,000 monthly
    assert parent.household_income == 75000.0
    assert parent.savings == 550000.0  # midpoint 3_8l
    assert parent.loan_max == 1150000.0  # midpoint 8_15l
    assert parent.monthly_surplus == 22500.0  # midpoint 15k_30k
    assert parent.existing_emis == 10000.0  # midpoint 5k_15k

    # Risk & preferences
    assert parent.risk == 0.0  # All safe
    assert parent.relocation_willingness == 0.0  # home_city
    assert parent.max_years_to_income == 6.0  # five_six
    assert parent.domain_ratings["business_management"] == 5.0
    assert parent.domain_ratings["tech_engineering"] == 1.0

    # Neutral uncollected defaults
    assert parent.min_salary == 300000.0
    assert parent.dependents == 1
    assert parent.sector_ratings.govt == 3
    assert parent.sector_ratings.private == 3


# ---------------------------------------------------------------------------
# Public Facade Tests
# ---------------------------------------------------------------------------
def test_public_facade_overall_conflict():
    """Verify overall_conflict returns conflict_index and 4 stable dimension gaps."""
    s_answers = {
        "pref_risk_1": "gamble",
        "pref_risk_2": "gamble",
        "pref_risk_3": "gamble",
        "pref_relocation": "abroad_ok",
        "pref_time_to_earn": "seven_plus",
        "pref_domain_wish": ["tech_engineering"],
    }
    p_answers = {
        "risk_1": "safe",
        "risk_2": "safe",
        "risk_3": "safe",
        "relocation": "home_city",
        "time_to_earn": "within_4y",
        "domain_wish": ["healthcare_medicine"],
    }
    student = student_from_answers(s_answers)
    parent = parent_from_answers(p_answers)

    res = overall_conflict(student, parent)

    assert "conflict_index" in res
    assert 0.0 <= res["conflict_index"] <= 100.0
    assert "dimension_gaps" in res
    gaps = res["dimension_gaps"]
    assert set(gaps.keys()) == {"risk", "domain", "relocation", "time"}
    for dim, gap in gaps.items():
        assert 0.0 <= gap <= 1.0

    assert "family_diagnosis_summary" in res
    assert "dimension_explanations" in res


def test_public_facade_per_career_scores_and_negotiate():
    """Verify per_career_scores and negotiate functions run and return expected structure."""
    student = student_from_answers({
        "pref_risk_1": "gamble",
        "pref_risk_2": "safe",
        "pref_risk_3": "safe",
    })
    parent = parent_from_answers({
        "risk_1": "safe",
        "risk_2": "safe",
        "risk_3": "safe",
    })

    # Per career scores
    scores = per_career_scores(student, parent)
    assert len(scores) > 0
    first = scores[0]
    assert "career_id" in first
    assert "student_fit" in first
    assert "family_viability" in first
    assert "composite_score" in first
    assert "is_viable" in first
    assert "data_complete" in first
    assert "missing_data_fields" in first

    # Negotiate
    neg = negotiate(student, parent, alpha=0.5)
    assert neg["alpha"] == 0.5
    assert "ranked_careers" in neg
    assert len(neg["ranked_careers"]) > 0
    assert "compromise_zone_career_ids" in neg
    assert "pareto_optimal_career_ids" in neg


def test_public_facade_unified_roadmap():
    """Verify unified_roadmap generates FullRoadmapReport with additive completeness fields."""
    student = student_from_answers({
        "bg_stream": "science_maths",
        "bg_marks_band": "75_90",
        "pref_risk_1": "safe",
        "pref_risk_2": "safe",
        "pref_risk_3": "safe",
    })
    parent = parent_from_answers({
        "income_band": "6_12l",
        "savings_band": "3_8l",
        "loan_band": "8_15l",
        "risk_1": "safe",
        "risk_2": "safe",
        "risk_3": "safe",
    })

    report = unified_roadmap(student, parent, alpha=0.50)
    assert report.student_id == "student"
    assert len(report.ranked_careers) > 0

    first = report.ranked_careers[0]
    assert hasattr(first, "data_complete")
    assert hasattr(first, "missing_data_fields")
    assert isinstance(first.data_complete, bool)
    assert isinstance(first.missing_data_fields, list)

