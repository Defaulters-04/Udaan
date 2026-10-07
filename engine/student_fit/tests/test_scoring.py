"""
test_scoring.py
UDAAN PRISM Engine — Student Fit Unit & Property Test Suite

Tests all pure-math formulations:
- Pearson correlation & InterestFit
- AptitudeFit shortfall penalties & zero denominator
- SkillFit ratio attainment, missing skills & R_k=0
- PersonalityFit RMS distance & clamping
- Academic gate G_acad evaluation & detailed failure reasons
- Composite F_student calculation with stage weights
- SWOT diagnostic extraction (strengths & weaknesses)
- Input validation & scale clamping [0, 1]
- Career ranking & separate blocked list
- JSON serialization
"""

import json
import math
import os
import sys
import pytest

# Ensure repository root is on sys.path for direct pytest runner invocation
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from engine.student_fit.config import STAGE_WEIGHTS
from engine.student_fit.models import (
    AcademicProfile,
    AcademicRequirement,
    Career,
    Result,
    Student,
)
from engine.student_fit.scoring import (
    calculate_aptitude_fit,
    calculate_interest_fit,
    calculate_personality_fit,
    calculate_skill_fit,
    calculate_student_fit,
    evaluate_academic_gate,
    rank_careers,
)
from engine.student_fit.swot import extract_strengths, extract_weaknesses


# ==============================================================================
# 1. Pearson Correlation & InterestFit Tests
# ==============================================================================

def test_interest_fit_identical_profiles():
    """Identical RIASEC vectors produce Pearson r = 1.0 -> InterestFit = 100.0."""
    I_s = {"R": 0.2, "I": 0.8, "A": 0.4, "S": 0.1, "E": 0.5, "C": 0.9}
    I_c = {"R": 0.2, "I": 0.8, "A": 0.4, "S": 0.1, "E": 0.5, "C": 0.9}
    score = calculate_interest_fit(I_s, I_c)
    assert math.isclose(score, 100.0, abs_tol=1e-3)


def test_interest_fit_opposite_profiles():
    """Perfect linearly opposite RIASEC vectors produce Pearson r = -1.0 -> InterestFit = 0.0."""
    I_s = {"R": 0.1, "I": 0.2, "A": 0.3, "S": 0.7, "E": 0.8, "C": 0.9}
    I_c = {"R": 0.9, "I": 0.8, "A": 0.7, "S": 0.3, "E": 0.2, "C": 0.1}
    score = calculate_interest_fit(I_s, I_c)
    assert math.isclose(score, 0.0, abs_tol=1e-3)


def test_interest_fit_zero_variance_flat_student_profile():
    """If student profile has zero variance (flat vector), InterestFit = 50.0 (neutral)."""
    I_s = {"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5}
    I_c = {"R": 0.1, "I": 0.8, "A": 0.3, "S": 0.4, "E": 0.6, "C": 0.2}
    score = calculate_interest_fit(I_s, I_c)
    assert math.isclose(score, 50.0, abs_tol=1e-3)


def test_interest_fit_zero_variance_flat_career_profile():
    """If career profile has zero variance, InterestFit = 50.0 (neutral)."""
    I_s = {"R": 0.2, "I": 0.7, "A": 0.4, "S": 0.1, "E": 0.9, "C": 0.3}
    I_c = {"R": 0.6, "I": 0.6, "A": 0.6, "S": 0.6, "E": 0.6, "C": 0.6}
    score = calculate_interest_fit(I_s, I_c)
    assert math.isclose(score, 50.0, abs_tol=1e-3)


def test_interest_fit_intermediate_correlation():
    """Verified known correlation produces exact mathematical result."""
    # List format input verification
    I_s = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    I_c = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    score = calculate_interest_fit(I_s, I_c)
    assert math.isclose(score, 100.0, abs_tol=1e-3)


# ==============================================================================
# 2. AptitudeFit Tests
# ==============================================================================

def test_aptitude_fit_student_at_or_above_requirement():
    """Student with a_j >= c_j on all traits gets AptitudeFit = 100.0."""
    a_j = {"logical": 0.8, "numerical": 0.7, "verbal": 0.6, "spatial": 0.5}
    c_j = {"logical": 0.8, "numerical": 0.7, "verbal": 0.6, "spatial": 0.5}
    u_j = {"logical": 0.9, "numerical": 0.8, "verbal": 0.5, "spatial": 0.4}
    score = calculate_aptitude_fit(a_j, c_j, u_j)
    assert math.isclose(score, 100.0, abs_tol=1e-3)


def test_aptitude_fit_excess_not_penalized_and_no_unearned_bonus():
    """Surplus on some traits (a_j > c_j) does not inflate score beyond 100.0."""
    a_j = {"logical": 1.0, "numerical": 1.0, "verbal": 1.0, "spatial": 1.0}
    c_j = {"logical": 0.5, "numerical": 0.5, "verbal": 0.5, "spatial": 0.5}
    u_j = {"logical": 1.0, "numerical": 1.0, "verbal": 1.0, "spatial": 1.0}
    score = calculate_aptitude_fit(a_j, c_j, u_j)
    assert math.isclose(score, 100.0, abs_tol=1e-3)


def test_aptitude_fit_shortfall_reduces_score_proportionally():
    """Shortfall reduces AptitudeFit strictly according to formula."""
    # c_j = 0.5, 0.5; u_j = 1.0, 1.0 -> Denom = 1.0
    # a_j = 0.25 on trait 1 (shortfall 0.25), a_j = 0.5 on trait 2 (shortfall 0)
    # Total shortfall = 1.0 * 0.25 = 0.25 -> 100 * (1 - 0.25 / 1.0) = 75.0
    a_j = {"logical": 0.25, "numerical": 0.50}
    c_j = {"logical": 0.50, "numerical": 0.50}
    u_j = {"logical": 1.00, "numerical": 1.00}
    score = calculate_aptitude_fit(a_j, c_j, u_j)
    assert math.isclose(score, 75.0, abs_tol=1e-3)


def test_aptitude_fit_zero_denominator():
    """If sum_j u_j * c_j == 0, AptitudeFit = 100.0."""
    a_j = {"logical": 0.0, "numerical": 0.0}
    c_j = {"logical": 0.0, "numerical": 0.0}
    u_j = {"logical": 1.0, "numerical": 1.0}
    score = calculate_aptitude_fit(a_j, c_j, u_j)
    assert math.isclose(score, 100.0, abs_tol=1e-3)


def test_aptitude_fit_zero_student_aptitude():
    """If student has 0 on all required aptitudes, score is 0.0."""
    a_j = {"logical": 0.0, "numerical": 0.0}
    c_j = {"logical": 0.8, "numerical": 0.6}
    u_j = {"logical": 1.0, "numerical": 1.0}
    score = calculate_aptitude_fit(a_j, c_j, u_j)
    assert math.isclose(score, 0.0, abs_tol=1e-3)


# ==============================================================================
# 3. SkillFit Tests
# ==============================================================================

def test_skill_fit_all_skills_met():
    """Student with P_k >= R_k gets SkillFit = 100.0."""
    P_k = {"python": 0.8, "sql": 0.7}
    R_k = {"python": 0.8, "sql": 0.7}
    s_k = {"python": 1.0, "sql": 1.0}
    score = calculate_skill_fit(P_k, R_k, s_k)
    assert math.isclose(score, 100.0, abs_tol=1e-3)


def test_skill_fit_missing_student_skill_counts_as_zero():
    """Missing student skill counts as 0."""
    P_k = {"python": 0.8}  # sql missing
    R_k = {"python": 0.8, "sql": 0.8}
    s_k = {"python": 1.0, "sql": 1.0}
    # python term = 1.0, sql term = 0.0 -> sum = 1.0 / 2.0 = 50.0
    score = calculate_skill_fit(P_k, R_k, s_k)
    assert math.isclose(score, 50.0, abs_tol=1e-3)


def test_skill_fit_rk_zero_counts_as_one():
    """If R_k = 0, treat that term as 1."""
    P_k = {"python": 0.0}
    R_k = {"python": 0.0}
    s_k = {"python": 1.0}
    score = calculate_skill_fit(P_k, R_k, s_k)
    assert math.isclose(score, 100.0, abs_tol=1e-3)


def test_skill_fit_no_skills_required():
    """If no skills are required (empty R_k), SkillFit = 100.0."""
    score = calculate_skill_fit({}, {}, {})
    assert math.isclose(score, 100.0, abs_tol=1e-3)


def test_skill_fit_partial_proportional_attainment():
    """Partial skill attainment scales proportionally up to 1.0."""
    P_k = {"python": 0.4}
    R_k = {"python": 0.8}
    s_k = {"python": 1.0}
    # term = min(1, 0.4 / 0.8) = 0.5 -> 50.0
    score = calculate_skill_fit(P_k, R_k, s_k)
    assert math.isclose(score, 50.0, abs_tol=1e-3)


# ==============================================================================
# 4. PersonalityFit Tests
# ==============================================================================

def test_personality_fit_identical_profile():
    """Identical personality traits produce distance 0 -> PersonalityFit = 100.0."""
    P_j = {"openness": 0.8, "conscientiousness": 0.7}
    Pc_j = {"openness": 0.8, "conscientiousness": 0.7}
    v_j = {"openness": 1.0, "conscientiousness": 1.0}
    score = calculate_personality_fit(P_j, Pc_j, v_j)
    assert math.isclose(score, 100.0, abs_tol=1e-3)


def test_personality_fit_distance_penalty():
    """Distance reduces score proportionally."""
    # diff = 0.2 on both traits, v_j = 1.0 -> RMS = 0.2 -> 100 * (1 - 0.2) = 80.0
    P_j = {"openness": 0.6, "conscientiousness": 0.5}
    Pc_j = {"openness": 0.8, "conscientiousness": 0.7}
    v_j = {"openness": 1.0, "conscientiousness": 1.0}
    score = calculate_personality_fit(P_j, Pc_j, v_j)
    assert math.isclose(score, 80.0, abs_tol=1e-3)


def test_personality_fit_clamping_to_zero():
    """Extreme difference clamps result to 0.0 (does not go negative)."""
    P_j = {"openness": 0.0}
    Pc_j = {"openness": 1.0}
    v_j = {"openness": 1.0}
    # RMS = 1.0 -> 100 * (1 - 1.0) = 0.0
    score = calculate_personality_fit(P_j, Pc_j, v_j)
    assert math.isclose(score, 0.0, abs_tol=1e-3)


# ==============================================================================
# 5. Academic Gate (G_acad) Tests
# ==============================================================================

def test_academic_gate_all_requirements_met():
    """When all mandatory academic criteria are met, G_acad = 1, blocked = False."""
    acad = AcademicProfile(
        marks=75.0,
        subjects={"mathematics", "physics", "chemistry"},
        exams={"jee main"},
    )
    req = AcademicRequirement(
        min_marks=60.0,
        required_subjects=["mathematics", "physics"],
        required_exams=["jee main"],
    )
    g_acad, reasons = evaluate_academic_gate(acad, req)
    assert g_acad == 1
    assert len(reasons) == 0


def test_academic_gate_failing_min_marks():
    """Failing minimum marks sets G_acad = 0 with descriptive human-readable reason."""
    acad = AcademicProfile(marks=55.0, subjects={"mathematics"}, exams=set())
    req = AcademicRequirement(min_marks=60.0, required_subjects=["mathematics"])
    g_acad, reasons = evaluate_academic_gate(acad, req)
    assert g_acad == 0
    assert len(reasons) == 1
    assert "minimum requirement" in reasons[0]


def test_academic_gate_missing_subjects():
    """Missing required subjects sets G_acad = 0 with descriptive reason."""
    acad = AcademicProfile(marks=80.0, subjects={"mathematics"}, exams=set())
    req = AcademicRequirement(
        min_marks=60.0, required_subjects=["mathematics", "physics", "chemistry"]
    )
    g_acad, reasons = evaluate_academic_gate(acad, req)
    assert g_acad == 0
    assert any("chemistry" in r and "physics" in r for r in reasons)


def test_academic_gate_missing_qualifying_exam():
    """Missing required qualifying exam sets G_acad = 0 with descriptive reason."""
    acad = AcademicProfile(
        marks=85.0, subjects={"physics", "chemistry", "biology"}, exams=set()
    )
    req = AcademicRequirement(
        min_marks=60.0,
        required_subjects=["biology"],
        required_exams=["neet"],
    )
    g_acad, reasons = evaluate_academic_gate(acad, req)
    assert g_acad == 0
    assert any("neet" in r for r in reasons)


# ==============================================================================
# 6. Composite Fit F_student & Stage Weights Tests
# ==============================================================================

def test_composite_fit_school_stage_skips_skill_fit():
    """School stage uses weights w_I=0.55, w_A=0.35, w_S=0.00, w_P=0.10."""
    student = Student(
        student_id="test_school",
        stage="school",
        I_s={"R": 0.2, "I": 0.8, "A": 0.3, "S": 0.1, "E": 0.4, "C": 0.7},
        a_j={"logical": 0.8, "numerical": 0.8, "verbal": 0.6, "spatial": 0.5},
        P_k={"python": 0.0},  # Even with 0 skill, skill weight is 0.0
        P_j={"openness": 0.8, "conscientiousness": 0.8},
        academics=AcademicProfile(marks=80.0),
    )
    career = Career(
        career_id="test_career",
        career_name="Test Career",
        I_c={"R": 0.2, "I": 0.8, "A": 0.3, "S": 0.1, "E": 0.4, "C": 0.7},  # Interest = 100
        c_j={"logical": 0.8, "numerical": 0.8, "verbal": 0.6, "spatial": 0.5},  # Aptitude = 100
        u_j={"logical": 1.0, "numerical": 1.0, "verbal": 1.0, "spatial": 1.0},
        R_k={"python": 1.0},  # High skill required, but school weight = 0.0
        s_k={"python": 1.0},
        Pc_j={"openness": 0.8, "conscientiousness": 0.8},  # Personality = 100
        v_j={"openness": 1.0, "conscientiousness": 1.0},
        academic_requirements=AcademicRequirement(min_marks=50.0),
    )
    res = calculate_student_fit(student, career)
    assert res.SkillFit == 0.0  # Skipped
    assert res.weights_used["w_S"] == 0.00
    assert math.isclose(res.F_student, 100.0, abs_tol=1e-3)


def test_composite_fit_college_stage_incorporates_skills():
    """College stage uses weights w_I=0.40, w_A=0.30, w_S=0.20, w_P=0.10."""
    student = Student(
        student_id="test_college",
        stage="college",
        I_s={"R": 0.2, "I": 0.8, "A": 0.3, "S": 0.1, "E": 0.4, "C": 0.7},
        a_j={"logical": 0.8, "numerical": 0.8, "verbal": 0.6, "spatial": 0.5},
        P_k={"python": 0.5},  # Half skill requirement met -> SkillFit = 50.0
        P_j={"openness": 0.8, "conscientiousness": 0.8},
        academics=AcademicProfile(marks=80.0),
    )
    career = Career(
        career_id="test_career",
        career_name="Test Career",
        I_c={"R": 0.2, "I": 0.8, "A": 0.3, "S": 0.1, "E": 0.4, "C": 0.7},  # 100
        c_j={"logical": 0.8, "numerical": 0.8, "verbal": 0.6, "spatial": 0.5},  # 100
        u_j={"logical": 1.0, "numerical": 1.0, "verbal": 1.0, "spatial": 1.0},
        R_k={"python": 1.0},
        s_k={"python": 1.0},
        Pc_j={"openness": 0.8, "conscientiousness": 0.8},  # 100
        v_j={"openness": 1.0, "conscientiousness": 1.0},
        academic_requirements=AcademicRequirement(min_marks=50.0),
    )
    res = calculate_student_fit(student, career)
    # Expected F_student = 0.40*100 + 0.30*100 + 0.20*50 + 0.10*100 = 40 + 30 + 10 + 10 = 90.0
    assert math.isclose(res.SkillFit, 50.0, abs_tol=1e-3)
    assert math.isclose(res.F_student, 90.0, abs_tol=1e-3)


def test_composite_fit_blocked_career_forces_zero_f_student():
    """If G_acad = 0, F_student is 0.0 even if all sub-scores are 100.0."""
    student = Student(
        student_id="test_blocked",
        stage="college",
        I_s={"R": 0.2, "I": 0.8, "A": 0.3, "S": 0.1, "E": 0.4, "C": 0.7},
        a_j={"logical": 0.8, "numerical": 0.8, "verbal": 0.6, "spatial": 0.5},
        P_k={"python": 1.0},
        P_j={"openness": 0.8, "conscientiousness": 0.8},
        academics=AcademicProfile(marks=45.0),  # Fails min marks 60.0
    )
    career = Career(
        career_id="test_career",
        career_name="Test Career",
        I_c={"R": 0.2, "I": 0.8, "A": 0.3, "S": 0.1, "E": 0.4, "C": 0.7},
        c_j={"logical": 0.8, "numerical": 0.8, "verbal": 0.6, "spatial": 0.5},
        u_j={"logical": 1.0, "numerical": 1.0, "verbal": 1.0, "spatial": 1.0},
        academic_requirements=AcademicRequirement(min_marks=60.0),
    )
    res = calculate_student_fit(student, career)
    assert res.G_acad == 0
    assert res.blocked is True
    assert res.F_student == 0.0
    # Sub-scores must still be preserved for diagnostic insight
    assert math.isclose(res.InterestFit, 100.0, abs_tol=1e-3)
    assert math.isclose(res.AptitudeFit, 100.0, abs_tol=1e-3)


# ==============================================================================
# 7. SWOT Extraction Tests
# ==============================================================================

def test_swot_strengths_extraction():
    """Identifies traits where a_j >= c_j and u_j >= mean(u)."""
    a_j = {"logical": 0.9, "numerical": 0.7, "verbal": 0.8, "spatial": 0.4}
    c_j = {"logical": 0.8, "numerical": 0.8, "verbal": 0.5, "spatial": 0.4}
    # u_j: mean = (0.9 + 0.8 + 0.4 + 0.3) / 4 = 0.60
    # Candidates >= mean: logical (0.9), numerical (0.8)
    # Meets requirement: logical (0.9 >= 0.8 -> surplus 0.1). numerical has shortfall (0.7 < 0.8)
    u_j = {"logical": 0.9, "numerical": 0.8, "verbal": 0.4, "spatial": 0.3}
    strengths = extract_strengths(a_j, c_j, u_j)
    assert len(strengths) == 1
    assert strengths[0]["trait"] == "logical"
    assert math.isclose(strengths[0]["surplus"], 0.1, abs_tol=1e-3)


def test_swot_weaknesses_extraction_capped_at_top_3():
    """Ranks traits by u_j * shortfall, only shortfall > 0, capped at top 3."""
    a_j = {"logical": 0.5, "numerical": 0.3, "verbal": 0.4, "spatial": 0.2}
    c_j = {"logical": 0.8, "numerical": 0.7, "verbal": 0.6, "spatial": 0.6}
    # shortfalls:
    # logical: 0.3 * 1.0 = 0.30
    # numerical: 0.4 * 0.9 = 0.36
    # verbal: 0.2 * 0.5 = 0.10
    # spatial: 0.4 * 0.4 = 0.16
    u_j = {"logical": 1.0, "numerical": 0.9, "verbal": 0.5, "spatial": 0.4}
    weaknesses = extract_weaknesses(a_j, c_j, u_j, max_count=3)
    assert len(weaknesses) == 3
    # Ordered by weighted shortfall: numerical (0.36), logical (0.30), spatial (0.16)
    assert weaknesses[0]["trait"] == "numerical"
    assert weaknesses[1]["trait"] == "logical"
    assert weaknesses[2]["trait"] == "spatial"


# ==============================================================================
# 8. Input Validation & Error Handling Tests
# ==============================================================================

def test_input_validation_clamping():
    """Inputs outside [0, 1] are clamped safely to [0, 1]."""
    s = Student(
        student_id="clamp_test",
        stage="school",
        I_s={"R": 1.5, "I": -0.2, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5},
        a_j={"logical": 1.2, "numerical": -0.5, "verbal": 0.5, "spatial": 0.5},
    )
    assert s.I_s["R"] == 1.0
    assert s.I_s["I"] == 0.0
    assert s.a_j["logical"] == 1.0
    assert s.a_j["numerical"] == 0.0


def test_input_validation_missing_riasec_keys_raises_error():
    """Missing RIASEC keys raises ValueError with clear error message."""
    with pytest.raises(ValueError, match="Missing required key"):
        Student(
            student_id="missing_riasec",
            stage="school",
            I_s={"R": 0.5, "I": 0.5},  # Missing A, S, E, C
            a_j={"logical": 0.5, "numerical": 0.5, "verbal": 0.5, "spatial": 0.5},
        )


def test_input_validation_missing_aptitude_keys_raises_error():
    """Missing core aptitude dimensions raises ValueError."""
    with pytest.raises(ValueError, match="Missing required key"):
        Student(
            student_id="missing_apt",
            stage="school",
            I_s={"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5},
            a_j={"logical": 0.5},  # Missing numerical, verbal, spatial
        )


def test_input_validation_invalid_stage_raises_error():
    """Invalid stage raises ValueError."""
    with pytest.raises(ValueError, match="Invalid stage"):
        Student(
            student_id="invalid_stage",
            stage="kindergarten",
            I_s={"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5},
            a_j={"logical": 0.5, "numerical": 0.5, "verbal": 0.5, "spatial": 0.5},
        )


# ==============================================================================
# 9. Career Ranking & Serialization Tests
# ==============================================================================

def test_rank_careers_sorting_and_blocked_separation():
    """rank_careers sorts eligible by F_student descending and preserves blocked careers."""
    student = Student(
        student_id="rank_test",
        stage="school",
        I_s={"R": 0.3, "I": 0.8, "A": 0.4, "S": 0.2, "E": 0.5, "C": 0.7},
        a_j={"logical": 0.8, "numerical": 0.8, "verbal": 0.7, "spatial": 0.6},
        academics=AcademicProfile(marks=75.0, subjects={"mathematics", "physics"}),
    )

    career_high_fit = Career(
        career_id="career_a_high",
        career_name="High Fit Career",
        I_c={"R": 0.3, "I": 0.8, "A": 0.4, "S": 0.2, "E": 0.5, "C": 0.7},
        c_j={"logical": 0.8, "numerical": 0.8, "verbal": 0.7, "spatial": 0.6},
        u_j={"logical": 1.0, "numerical": 1.0, "verbal": 1.0, "spatial": 1.0},
        academic_requirements=AcademicRequirement(min_marks=60.0),
    )

    career_med_fit = Career(
        career_id="career_b_med",
        career_name="Medium Fit Career",
        I_c={"R": 0.7, "I": 0.2, "A": 0.8, "S": 0.5, "E": 0.2, "C": 0.3},
        c_j={"logical": 0.8, "numerical": 0.8, "verbal": 0.7, "spatial": 0.6},
        u_j={"logical": 1.0, "numerical": 1.0, "verbal": 1.0, "spatial": 1.0},
        academic_requirements=AcademicRequirement(min_marks=60.0),
    )

    career_blocked = Career(
        career_id="career_c_blocked",
        career_name="Blocked Career",
        I_c={"R": 0.3, "I": 0.8, "A": 0.4, "S": 0.2, "E": 0.5, "C": 0.7},
        c_j={"logical": 0.8, "numerical": 0.8, "verbal": 0.7, "spatial": 0.6},
        u_j={"logical": 1.0, "numerical": 1.0, "verbal": 1.0, "spatial": 1.0},
        academic_requirements=AcademicRequirement(min_marks=90.0),  # Student fails (75 < 90)
    )

    ranking = rank_careers(student, [career_med_fit, career_blocked, career_high_fit])
    eligible, blocked = ranking.eligible, ranking.blocked

    assert len(eligible) == 2
    assert len(blocked) == 1
    assert eligible[0].career_id == "career_a_high"
    assert eligible[1].career_id == "career_b_med"
    assert eligible[0].F_student > eligible[1].F_student

    assert blocked[0].career_id == "career_c_blocked"
    assert blocked[0].F_student == 0.0
    assert blocked[0].blocked is True
    assert len(blocked[0].blocked_reasons) > 0


def test_result_to_dict_json_serialization():
    """Result.to_dict() must be fully JSON-serializable."""
    res = Result(
        career_id="sample_career",
        career_name="Sample Career",
        F_student=88.5,
        InterestFit=90.0,
        AptitudeFit=85.0,
        SkillFit=0.0,
        PersonalityFit=92.0,
        G_acad=1,
        stage="school",
        weights_used={"w_I": 0.55, "w_A": 0.35, "w_S": 0.0, "w_P": 0.1},
        strengths=[{"trait": "logical", "importance": 0.9}],
        weaknesses=[],
        blocked=False,
        blocked_reasons=[],
    )
    serialized = json.dumps(res.to_dict())
    assert isinstance(serialized, str)
    deserialized = json.loads(serialized)
    assert deserialized["career_id"] == "sample_career"
    assert deserialized["F_student"] == 88.5
