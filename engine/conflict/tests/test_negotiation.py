"""Unit tests for the PRISM Conflict Index Negotiation Explorer and Composite Blending."""

import pytest
from engine.conflict.config import ConflictConfig, DEFAULT_CONFIG
from engine.conflict.scores import (
    compute_overall_conflict,
    compute_career_conflict,
    compute_composite_score,
    evaluate_negotiation_slider,
    generate_conflict_explanations,
)
from engine.conflict.models import ScoredCareerInput
from engine.student_fit.models import Student, AcademicProfile
from engine.parent.models import ParentProfile, SectorRatings


def test_negotiation_slider_extremes():
    """Verify alpha=1.0 favors student fit, alpha=0.0 favors parent viability."""
    student = {
        "risk_appetite": 0.9,
        "domain_preference": {"Technology & Engineering": 5.0},
        "relocation_willingness": 0.8,
        "max_years_to_income": 4.0,
    }
    parent = {
        "risk": 0.2,
        "domain_ratings": {"Technology & Engineering": 3.0},
        "relocation_willingness": 0.2,
        "max_years_to_income": 3.0,
    }

    careers = [
        ScoredCareerInput(
            career_id="startup_founder",
            route_id="r1",
            career_name="Startup Founder",
            student_fit=0.95,
            family_viability=0.20,
            market_score=0.80,
            career_risk=0.90,
            domain="Technology & Engineering",
        ),
        ScoredCareerInput(
            career_id="govt_engineer",
            route_id="r2",
            career_name="Govt PSU Engineer",
            student_fit=0.30,
            family_viability=0.95,
            market_score=0.75,
            career_risk=0.10,
            domain="Technology & Engineering",
        ),
        ScoredCareerInput(
            career_id="software_consultant",
            route_id="r3",
            career_name="Software Consultant",
            student_fit=0.82,
            family_viability=0.85,
            market_score=0.88,
            career_risk=0.45,
            domain="Technology & Engineering",
        ),
    ]

    # Alpha = 1.0 (Student Priority)
    res_student = evaluate_negotiation_slider(student, parent, careers, alpha=1.0)
    assert res_student.ranked_careers[0].career_id == "startup_founder"

    # Alpha = 0.0 (Parent Priority)
    res_parent = evaluate_negotiation_slider(student, parent, careers, alpha=0.0)
    assert res_parent.ranked_careers[0].career_id == "govt_engineer"

    # Alpha = 0.5 (Compromise Priority)
    res_compromise = evaluate_negotiation_slider(student, parent, careers, alpha=0.5)
    assert res_compromise.ranked_careers[0].career_id == "software_consultant"
    assert res_compromise.ranked_careers[0].is_in_compromise_zone is True


def test_pareto_optimality_detection():
    """Verify Pareto frontier flags non-dominated options."""
    student = {"risk_appetite": 0.5}
    parent = {"risk": 0.5}

    careers = [
        ScoredCareerInput(
            career_id="c_dominated",
            route_id="r0",
            student_fit=0.40,
            family_viability=0.40,
        ),
        ScoredCareerInput(
            career_id="c_dominant",
            route_id="r1",
            student_fit=0.80,
            family_viability=0.80,
        ),
    ]

    res = evaluate_negotiation_slider(student, parent, careers, alpha=0.5)
    pareto_map = {c.career_id: c.is_pareto_optimal for c in res.ranked_careers}
    assert pareto_map["c_dominant"] is True
    assert pareto_map["c_dominated"] is False


def test_composite_score_blending():
    """Test composite score computation with conflict penalty."""
    # Zero conflict
    score_no_conflict = compute_composite_score(
        student_fit=0.80,
        family_viability=0.80,
        market_score=0.80,
        career_conflict=0.0,
    )
    assert score_no_conflict == pytest.approx(0.80)

    # High conflict reduces score
    score_high_conflict = compute_composite_score(
        student_fit=0.80,
        family_viability=0.80,
        market_score=0.80,
        career_conflict=1.0,
    )
    assert score_high_conflict < score_no_conflict
    # Penalty is conflict_penalty_weight * conflict * base = 0.15 * 1.0 * 0.80 = 0.12
    # 0.80 - 0.12 = 0.68
    assert score_high_conflict == pytest.approx(0.68)


def test_interoperability_with_student_and_parent_modules():
    """Test using actual Student and ParentProfile objects from other PRISM modules."""
    student = Student(
        student_id="stu_123",
        stage="college",
        I_s={"R": 0.8, "I": 0.7, "A": 0.3, "S": 0.2, "E": 0.5, "C": 0.4},
        a_j={"logical": 0.8, "numerical": 0.7, "verbal": 0.6, "spatial": 0.5},
        risk_appetite=0.75,
        domain_preference={"Technology & Engineering": 5.0, "Business": 4.0},
        relocation_willingness=0.80,
        max_years_to_income=4.0,
    )

    parent = ParentProfile(
        savings=1000000.0,
        monthly_surplus=50000.0,
        household_income=150000.0,
        existing_emis=10000.0,
        loan_max=1500000.0,
        domain_ratings={"Technology & Engineering": 4.0, "Business": 3.0},
        sector_ratings=SectorRatings(govt=4, private=4, entrepreneurship=2),
        min_salary=600000.0,
        max_years_to_income=4.0,
        relocation_willingness=0.60,
        risk=0.40,
    )

    report = compute_overall_conflict(student, parent)
    assert 0.0 <= report.overall_conflict <= 1.0
    assert report.risk_conflict.gap == pytest.approx(0.35)
    assert report.time_conflict.gap == pytest.approx(0.0)
    assert len(report.diagnosis_summary) > 0
