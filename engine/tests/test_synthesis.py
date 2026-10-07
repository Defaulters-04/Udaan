"""Tests for the PRISM Engine Synthesis & Unified Roadmap Layer."""

import pytest
from engine.student_fit.models import Student, Career as StudentCareer, AcademicProfile, AcademicRequirement
from engine.parent.models import ParentProfile, SectorRatings, Route
from engine.synthesis import generate_unified_roadmap, FullRoadmapReport, RoadmapItem, BlockedRoadmapItem


@pytest.fixture
def sample_student():
    return Student(
        student_id="student_deepa",
        stage="college",
        I_s={"R": 0.40, "I": 0.85, "A": 0.30, "S": 0.20, "E": 0.40, "C": 0.70},
        a_j={"logical": 0.85, "numerical": 0.80, "verbal": 0.60, "spatial": 0.50},
        P_k={"python": 0.80, "algorithms": 0.75},
        P_j={"openness": 0.70, "conscientiousness": 0.80},
        academics=AcademicProfile(marks=82.0, subjects={"mathematics", "physics"}),
        risk_appetite=0.80,
        domain_preference={"Technology & Engineering": 5.0, "Healthcare & Medicine": 2.0},
        relocation_willingness=0.80,
        max_years_to_income=4.0,
    )


@pytest.fixture
def sample_parent():
    return ParentProfile(
        savings=400000.0,
        monthly_surplus=8000.0,
        household_income=50000.0,
        existing_emis=2000.0,
        loan_max=500000.0,
        domain_ratings={"Technology & Engineering": 5.0, "Healthcare & Medicine": 3.0},
        sector_ratings=SectorRatings(govt=4, private=5, entrepreneurship=3),
        min_salary=600000.0,
        max_years_to_income=4.0,
        relocation_willingness=0.60,
        risk=0.40,
        dependents=2,
    )


@pytest.fixture
def sample_careers():
    # Career 1: Software Engineer (Good student match, affordable state route available)
    c1 = StudentCareer(
        career_id="software_engineer",
        career_name="Software Engineer",
        I_c={"R": 0.35, "I": 0.85, "A": 0.30, "S": 0.20, "E": 0.30, "C": 0.70},
        c_j={"logical": 0.80, "numerical": 0.70, "verbal": 0.50, "spatial": 0.40},
        u_j={"logical": 0.90, "numerical": 0.80, "verbal": 0.50, "spatial": 0.30},
        R_k={"python": 0.70, "algorithms": 0.60},
        s_k={"python": 0.90, "algorithms": 0.80},
        Pc_j={"openness": 0.70, "conscientiousness": 0.80},
        v_j={"openness": 0.60, "conscientiousness": 0.80},
        academic_requirements=AcademicRequirement(
            min_marks=60.0,
            required_subjects=["mathematics", "physics"],
        ),
    )

    # Career 2: Expensive Private Medicine (High academic gate, very expensive route)
    c2 = StudentCareer(
        career_id="clinical_doctor",
        career_name="Clinical Doctor",
        I_c={"R": 0.30, "I": 0.80, "A": 0.20, "S": 0.85, "E": 0.40, "C": 0.50},
        c_j={"logical": 0.70, "numerical": 0.50, "verbal": 0.75, "spatial": 0.60},
        u_j={"logical": 0.70, "numerical": 0.50, "verbal": 0.80, "spatial": 0.60},
        R_k={},
        s_k={},
        Pc_j={"agreeableness": 0.85, "conscientiousness": 0.80},
        v_j={"agreeableness": 0.80, "conscientiousness": 0.80},
        academic_requirements=AcademicRequirement(
            min_marks=95.0,  # Student marks 82.0 will fail this gate
            required_subjects=["biology"],  # Missing subject
        ),
    )

    return [c1, c2]


@pytest.fixture
def sample_routes():
    # Route 1: Affordable State Engineering Route for software_engineer
    r1 = Route(
        career_id="software_engineer",
        route_id="state_btech",
        tuition=200000.0,
        living=120000.0,
        exam_equipment=10000.0,
        grant=0.0,
        duration_years=4.0,
        starting_salary=750000.0,
        years_to_first_income=4.0,
        career_risk=0.40,
        relocation_need=0.50,
        domain="Technology & Engineering",
        sector="private",
    )

    # Route 2: Overly expensive private route for software_engineer
    r2 = Route(
        career_id="software_engineer",
        route_id="expensive_pvt_btech",
        tuition=2500000.0,
        living=600000.0,
        exam_equipment=20000.0,
        grant=0.0,
        duration_years=4.0,
        starting_salary=850000.0,
        years_to_first_income=4.0,
        career_risk=0.40,
        relocation_need=0.70,
        domain="Technology & Engineering",
        sector="private",
    )

    # Route 3: Unaffordable Private Medical College Route
    r3 = Route(
        career_id="clinical_doctor",
        route_id="pvt_medical_college",
        tuition=6000000.0,
        living=1000000.0,
        exam_equipment=50000.0,
        grant=0.0,
        duration_years=5.5,
        starting_salary=800000.0,
        years_to_first_income=5.5,
        career_risk=0.30,
        relocation_need=0.80,
        domain="Healthcare & Medicine",
        sector="private",
    )

    return [r1, r2, r3]


def test_unified_roadmap_generation(sample_student, sample_parent, sample_careers, sample_routes):
    """Verify end-to-end PRISM Engine synthesis pipeline."""
    report = generate_unified_roadmap(
        student=sample_student,
        parent=sample_parent,
        student_careers=sample_careers,
        routes=sample_routes,
        alpha=0.50,
    )

    assert isinstance(report, FullRoadmapReport)
    assert report.student_id == "student_deepa"
    assert 0.0 <= report.family_conflict_score <= 100.0
    assert len(report.family_diagnosis_summary) > 0

    # Software Engineer should be ranked and feasible
    assert len(report.ranked_careers) == 1
    top_c = report.ranked_careers[0]
    assert top_c.career_id == "software_engineer"
    assert top_c.best_route_id == "state_btech"  # picked the affordable state route over expensive pvt
    assert top_c.student_fit > 70.0
    assert top_c.family_viability > 70.0
    assert top_c.monthly_emi >= 0.0

    # Clinical doctor failed academic gate (marks 82 vs min 95, missing biology)
    blocked_ids = [b.career_id for b in report.blocked_careers]
    assert "clinical_doctor" in blocked_ids
    doctor_blocked = next(b for b in report.blocked_careers if b.career_id == "clinical_doctor")
    assert "G_acad" in doctor_blocked.failed_gates
    assert len(doctor_blocked.constructive_remedies) > 0


def test_unified_roadmap_financial_gate_blocking(sample_student, sample_parent, sample_careers, sample_routes):
    """When a career only has unaffordable routes, it gets placed into blocked_careers with remedies."""
    # Provide only the expensive private route for software_engineer
    expensive_routes = [r for r in sample_routes if r.route_id == "expensive_pvt_btech"]
    report = generate_unified_roadmap(
        student=sample_student,
        parent=sample_parent,
        student_careers=[sample_careers[0]],
        routes=expensive_routes,
    )

    assert len(report.ranked_careers) == 0
    assert len(report.blocked_careers) == 1
    blocked = report.blocked_careers[0]
    assert blocked.career_id == "software_engineer"
    assert "G_fin" in blocked.failed_gates
    assert len(blocked.constructive_remedies) > 0
