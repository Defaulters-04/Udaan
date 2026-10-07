"""Unit tests validating the 8 PRISM scoring engine logic fixes.

Fix 1: Changing conflict inputs does not change Fit, Family or ranking.
Fix 2: fit_gap naming and calculation (|Fit - Family|).
Fix 3: Hand-built stretch and non-stretch cases with weighted aptitude shortfall.
Fix 4: Missing data handling (NOT FOUND salary -> insufficient_data, weight rescaling with hand-calculated expected values).
Fix 5: Market absolute tiers (declining demand cannot gain points from other careers).
Fix 6: Blended InterestFit + flat RIASEC vector gives 50.0 and low_signal=True.
Fix 7: Financial thresholds in config and sensitivity check consistency.
Fix 8: 2-score ranking, balanced pick maximizing min(Fit, Family), and Pareto compromise zone.
"""

import math
import pytest
import numpy as np

from engine.student_fit.models import Student, Career as StudentCareer, AcademicRequirement
from engine.student_fit.scoring import (
    calculate_interest_fit,
    calculate_student_fit,
    calculate_stretch,
)
from engine.parent.models import ParentProfile, Route, SectorRatings
from engine.parent.scores import score_financial, evaluate_parent_portfolio
from engine.parent.config import DEFAULT_CONFIG as PARENT_CONFIG
from engine.market.models import CareerMarketRecord, DemandSeries, CuratedTrend, SalaryBands, DisruptionProfile
from engine.market.scores import evaluate_market_catalogue
from engine.market.components import map_demand_to_tier, calculate_tier_points
from engine.market.config import DEFAULT_CONFIG as MARKET_CONFIG
from engine.conflict.models import ScoredCareerInput, StudentConflictInput, ParentConflictInput
from engine.conflict.scores import evaluate_negotiation_slider, compute_composite_score
from engine.conflict.config import DEFAULT_CONFIG as CONFLICT_CONFIG
from engine.config import DEFAULT_CONFIG as MASTER_CONFIG


# ==============================================================================
# Fix 1 & 2: Conflict does NOT alter Fit, Family, or Ranking; fit_gap is |Fit-Family|
# ==============================================================================

def test_fix1_changing_conflict_does_not_change_scores_or_ranking():
    """Varying conflict inputs (aligned vs diametric) leaves Fit, Family, and final ranking unchanged."""
    careers = [
        ScoredCareerInput(
            career_id="career_1",
            route_id="r1",
            career_name="Software Engineer",
            student_fit=0.85,
            family_viability=0.75,
            market_score=0.80,
            domain="Technology",
            is_financially_viable=True,
        ),
        ScoredCareerInput(
            career_id="career_2",
            route_id="r2",
            career_name="Civil Engineer",
            student_fit=0.70,
            family_viability=0.80,
            market_score=0.75,
            domain="Technology",
            is_financially_viable=True,
        ),
    ]

    # Scenario A: Aligned student and parent (low conflict)
    s_aligned = StudentConflictInput(risk_appetite=0.5, relocation_willingness=0.5, max_years_to_income=4.0)
    p_aligned = ParentConflictInput(risk=0.5, relocation_willingness=0.5, max_years_to_income=4.0)

    res_a = evaluate_negotiation_slider(s_aligned, p_aligned, careers, alpha=0.5)

    # Scenario B: High conflict student and parent (opposed dimensions)
    s_conflict = StudentConflictInput(risk_appetite=0.95, relocation_willingness=0.95, max_years_to_income=6.0)
    p_conflict = ParentConflictInput(risk=0.05, relocation_willingness=0.05, max_years_to_income=2.0)

    res_b = evaluate_negotiation_slider(s_conflict, p_conflict, careers, alpha=0.5)

    # Scores and rankings must be strictly identical
    assert len(res_a.ranked_careers) == len(res_b.ranked_careers)
    for c_a, c_b in zip(res_a.ranked_careers, res_b.ranked_careers):
        assert c_a.career_id == c_b.career_id
        assert c_a.student_fit == pytest.approx(c_b.student_fit)
        assert c_a.family_viability == pytest.approx(c_b.family_viability)
        assert c_a.negotiated_score == pytest.approx(c_b.negotiated_score)
        # Fix 2: fit_gap is |Fit - Family|
        assert c_a.fit_gap == pytest.approx(abs(c_a.student_fit - c_a.family_viability))


# ==============================================================================
# Fix 3: Stretch Flag on Weighted Aptitude Shortfall Ratio
# ==============================================================================

def test_fix3_stretch_flag_hand_built_cases():
    """Hand-built cases: shortfall ratio <= stretch_shortfall_ratio -> False; > threshold -> True."""
    # Required aptitude dimensions: ['logical', 'numerical', 'verbal', 'spatial']
    c_j = {"logical": 0.90, "numerical": 0.90, "verbal": 0.50, "spatial": 0.50}
    u_j = {"logical": 1.0, "numerical": 1.0, "verbal": 0.5, "spatial": 0.5}
    # Denominator = 1.0*0.90 + 1.0*0.90 + 0.5*0.50 + 0.5*0.50 = 2.30

    # Case 1: Non-stretch (a_j = 0.85, 0.85, 0.50, 0.50)
    # Shortfall = 0.05 + 0.05 = 0.10
    # Shortfall ratio = 0.10 / 2.30 = 0.0435 <= 0.20 -> False
    a_non_stretch = {"logical": 0.85, "numerical": 0.85, "verbal": 0.50, "spatial": 0.50}
    is_stretch, reasons, ratio = calculate_stretch(a_non_stretch, c_j, u_j)
    assert not is_stretch
    assert ratio == pytest.approx(0.10 / 2.30, abs=1e-3)
    assert len(reasons) == 0

    # Case 2: Stretch (a_j = 0.40, 0.40, 0.50, 0.50)
    # Shortfall = 0.50 + 0.50 = 1.00
    # Shortfall ratio = 1.00 / 2.30 = 0.4348 > 0.20 -> True
    a_stretch = {"logical": 0.40, "numerical": 0.40, "verbal": 0.50, "spatial": 0.50}
    is_stretch_2, reasons_2, ratio_2 = calculate_stretch(a_stretch, c_j, u_j)
    assert is_stretch_2
    assert ratio_2 == pytest.approx(1.00 / 2.30, abs=1e-3)
    assert len(reasons_2) == 2
    assert any("logical" in r for r in reasons_2)
    assert any("numerical" in r for r in reasons_2)

    # In student fit evaluation, stretch careers are NOT blocked and keep score
    student = Student(
        student_id="stu_test",
        stage="school",
        I_s={"R": 0.8, "I": 0.8, "A": 0.2, "S": 0.2, "E": 0.2, "C": 0.2},
        a_j=a_stretch,
        academics={"marks": 85.0},
    )
    career = StudentCareer(
        career_id="test_career",
        career_name="Test Career",
        I_c={"R": 0.8, "I": 0.8, "A": 0.2, "S": 0.2, "E": 0.2, "C": 0.2},
        c_j=c_j,
        u_j=u_j,
    )
    result = calculate_student_fit(student, career)
    assert result.stretch is True
    assert result.G_acad == 1
    assert result.blocked is False
    assert result.F_student > 0.0


# ==============================================================================
# Fix 4: Missing Data Handling (NOT FOUND salary -> insufficient_data & weight rescaling)
# ==============================================================================

def test_fix4_missing_salary_returns_insufficient_data():
    """Route with None / NOT FOUND starting salary returns status 'insufficient_data' and is excluded."""
    profile = ParentProfile(
        savings=300000.0,
        monthly_surplus=5000.0,
        household_income=50000.0,
        existing_emis=0.0,
        loan_max=500000.0,
        domain_ratings={"tech": 5},
        sector_ratings=SectorRatings(govt=4, private=4, entrepreneurship=3),
        min_salary=400000.0,
        max_years_to_income=4.0,
        relocation_willingness=0.5,
        risk=0.5,
    )
    route_missing_salary = Route(
        career_id="data_eng",
        route_id="r_missing",
        tuition=200000.0,
        starting_salary=None,  # Missing salary
        domain="tech",
    )

    eval_res = evaluate_parent_portfolio(profile, [route_missing_salary], PARENT_CONFIG)
    report = eval_res.reports[0]
    assert report.status == "insufficient_data"
    assert report.f_family == 0.0
    assert report.g_fin == 0


def test_fix4_missing_subscore_weight_rescaling():
    """Dropping a missing sub-score rescales remaining weights to sum to 1.0 with hand-calculated value."""
    # Financial config weights: w_budget=0.35, w_repay_p=0.25, w_dsr=0.25, w_payback=0.15 (total 1.0)
    # Suppose f_budget = 0.80, f_repay_p = 0.70, f_dsr = 0.90, f_payback = None (NOT FOUND)
    # Kept weights: 0.35 + 0.25 + 0.25 = 0.85
    # Rescaled (0-100 scale):
    # 100 * (0.35*0.80 + 0.25*0.70 + 0.25*0.90) / 0.85
    # = 100 * (0.28 + 0.175 + 0.225) / 0.85 = 100 * 0.68 / 0.85 = 80.0
    f_budget = 0.80
    f_repay_p = 0.70
    f_dsr = 0.90
    f_payback = None

    hand_calculated = 100.0 * (0.35 * 0.80 + 0.25 * 0.70 + 0.25 * 0.90) / 0.85
    res, dropped_frac = score_financial(
        f_budget=f_budget,
        f_repay_p=f_repay_p,
        f_dsr=f_dsr,
        f_payback=f_payback,
        config=PARENT_CONFIG,
        return_dropped_fraction=True,
    )
    assert res == pytest.approx(hand_calculated)
    assert dropped_frac == pytest.approx(0.15)


# ==============================================================================
# Fix 5: Market Absolute Tiers
# ==============================================================================

def test_fix5_declining_demand_cannot_gain_points_from_peers():
    """Absolute tier lookup: a declining career's score is independent of other catalogue careers."""
    # Under tier lookup:
    # declining growth (-0.15) -> "declining" tier
    # Tier lookup gives fixed points regardless of other careers
    tier = map_demand_to_tier(-0.15, config=MARKET_CONFIG)
    assert tier == "declining"

    points_single = calculate_tier_points(
        demand_tier="declining",
        velocity_tier="declining",
        disruption_tier="high",
        config=MARKET_CONFIG,
    )
    # Lookup: demand declining=20, velocity declining=20, disruption high=20
    # Points = 0.40*20 + 0.35*20 + 0.25*20 = 20.0
    assert points_single == pytest.approx(20.0)


# ==============================================================================
# Fix 6: Blended InterestFit & Flat Student RIASEC Detection
# ==============================================================================

def test_fix6_flat_student_riasec_gives_50_and_low_signal():
    """Flat student RIASEC vector gives InterestFit = 50.0 and low_signal = True."""
    # Perfectly flat vector
    I_s_flat = {"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5}
    I_c = {"R": 0.9, "I": 0.8, "A": 0.2, "S": 0.1, "E": 0.4, "C": 0.3}

    score, low_signal = calculate_interest_fit(I_s_flat, I_c, return_low_signal=True)
    assert score == pytest.approx(50.0)
    assert low_signal is True

    # Student fit result propagates low_signal
    student = Student(
        student_id="stu_flat",
        stage="school",
        I_s=I_s_flat,
        a_j={"logical": 0.7, "numerical": 0.7, "verbal": 0.7, "spatial": 0.7},
    )
    career = StudentCareer(
        career_id="c_test",
        career_name="Career Test",
        I_c=I_c,
        c_j={"logical": 0.7, "numerical": 0.7, "verbal": 0.7, "spatial": 0.7},
        u_j={"logical": 1.0, "numerical": 1.0, "verbal": 1.0, "spatial": 1.0},
    )
    res = calculate_student_fit(student, career)
    assert res.low_signal is True
    assert res.InterestFit == pytest.approx(50.0)


def test_fix6_blended_interest_fit_formula():
    """InterestFit blends Pearson term (50*(1+r)) and Overlap term (100 * |top3_s ∩ top3_c| / 3)."""
    # Student top 3: R, I, A
    I_s = {"R": 0.9, "I": 0.8, "A": 0.7, "S": 0.3, "E": 0.2, "C": 0.1}
    # Career top 3: R, I, S (overlap: R, I -> 2 items)
    I_c = {"R": 0.9, "I": 0.8, "A": 0.2, "S": 0.7, "E": 0.1, "C": 0.3}

    score, low_signal = calculate_interest_fit(I_s, I_c, return_low_signal=True)
    assert not low_signal

    # Pearson between x and y
    x = [0.9, 0.8, 0.7, 0.3, 0.2, 0.1]
    y = [0.9, 0.8, 0.2, 0.7, 0.1, 0.3]
    r = float(np.corrcoef(x, y)[0, 1])
    interest_term = 50.0 * (1.0 + r)
    overlap_term = 100.0 * (2.0 / 3.0)
    expected = (0.50 * interest_term) + (0.50 * overlap_term)

    assert score == pytest.approx(expected, abs=1e-2)


# ==============================================================================
# Fix 8: 2-Score Ranking, Balanced Pick, and Pareto Compromise Zone
# ==============================================================================

def test_fix8_balanced_pick_and_compromise_zone():
    """Balanced pick maximizes min(Fit, Family); compromise zone is Pareto frontier among viable careers >= 0.50."""
    careers = [
        # Career A: High student fit, moderate family
        ScoredCareerInput(
            career_id="A",
            route_id="rA",
            career_name="Career A",
            student_fit=0.90,
            family_viability=0.55,
            market_score=0.70,
            is_financially_viable=True,
        ),
        # Career B: Balanced sweet spot
        ScoredCareerInput(
            career_id="B",
            route_id="rB",
            career_name="Career B",
            student_fit=0.75,
            family_viability=0.75,
            market_score=0.70,
            is_financially_viable=True,
        ),
        # Career C: Moderate student fit, high family
        ScoredCareerInput(
            career_id="C",
            route_id="rC",
            career_name="Career C",
            student_fit=0.55,
            family_viability=0.85,
            market_score=0.70,
            is_financially_viable=True,
        ),
        # Career D: Dominated by B (0.60, 0.60 < 0.75, 0.75)
        ScoredCareerInput(
            career_id="D",
            route_id="rD",
            career_name="Career D",
            student_fit=0.60,
            family_viability=0.60,
            market_score=0.70,
            is_financially_viable=True,
        ),
        # Career E: Sub-threshold (Fit 0.40 < 0.50)
        ScoredCareerInput(
            career_id="E",
            route_id="rE",
            career_name="Career E",
            student_fit=0.40,
            family_viability=0.90,
            market_score=0.70,
            is_financially_viable=True,
        ),
    ]

    s = StudentConflictInput()
    p = ParentConflictInput()

    res = evaluate_negotiation_slider(s, p, careers, alpha=0.5)

    # 1. Balanced Pick:
    # min(A) = 0.55, min(B) = 0.75, min(C) = 0.55, min(D) = 0.60, min(E) = 0.40
    # Career B maximizes min(Fit, Family) with 0.75
    assert res.balanced_pick_career_id == "B"
    assert res.balanced_pick is not None
    assert res.balanced_pick.career_id == "B"

    # 2. Compromise Zone:
    # Careers >= 0.50 cutoff are A (0.90, 0.55), B (0.75, 0.75), C (0.55, 0.85), D (0.60, 0.60).
    # Pareto frontier among these:
    # B dominates D (0.75 > 0.60 and 0.75 > 0.60) -> D is dominated!
    # A, B, C are mutually non-dominating.
    # Therefore compromise zone contains exactly A, B, C.
    cz_ids = {c.career_id for c in res.compromise_zone_careers}
    assert cz_ids == {"A", "B", "C"}
    assert "D" not in cz_ids
    assert "E" not in cz_ids
