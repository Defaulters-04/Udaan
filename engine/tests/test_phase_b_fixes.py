"""Test suite for Phase B Engine Fixes (B1, B2, B3, B4).

B1: Same best route in negotiate() and unified_roadmap() across demo careers and government routes.
B2: No intermediate rounding, deterministic tie-breaking (higher score, then career_id ascending).
B3: Structured block_cause (academic, no_route_data, cost) with priority academic > no_route_data > cost.
B4: Missing market signals return "NOT FOUND", market_is_default=True, confidence="low", not numeric.
"""

import random
import pytest

from engine.student_fit.models import Student, Career as StudentCareer, AcademicProfile, AcademicRequirement
from engine.parent.models import ParentProfile, SectorRatings, Route
from engine.conflict.models import ScoredCareerInput, StudentConflictInput, ParentConflictInput
from engine.conflict.scores import evaluate_negotiation_slider
from engine.synthesis import generate_unified_roadmap, FullRoadmapReport, BlockedRoadmapItem
from engine.public import per_career_scores, negotiate, unified_roadmap, get_default_student_careers, get_default_routes


@pytest.fixture
def demo_student():
    return Student(
        student_id="student_demo",
        stage="college",
        I_s={"R": 0.35, "I": 0.85, "A": 0.30, "S": 0.20, "E": 0.30, "C": 0.70},
        a_j={"logical": 0.85, "numerical": 0.80, "verbal": 0.70, "spatial": 0.60},
        P_k={"python": 0.80, "circuits": 0.70},
        P_j={"openness": 0.70, "conscientiousness": 0.80},
        academics=AcademicProfile(marks=85.0, subjects={"mathematics", "physics", "chemistry"}),
        risk_appetite=0.50,
        domain_preference={"Technology & Engineering": 5.0, "Healthcare & Medicine": 3.0},
        relocation_willingness=0.70,
        max_years_to_income=4.0,
    )


@pytest.fixture
def demo_parent():
    return ParentProfile(
        savings=500000.0,
        monthly_surplus=12000.0,
        household_income=65000.0,
        existing_emis=3000.0,
        loan_max=600000.0,
        domain_ratings={"Technology & Engineering": 5.0, "Healthcare & Medicine": 4.0},
        sector_ratings=SectorRatings(govt=5, private=4, entrepreneurship=3),
        min_salary=500000.0,
        max_years_to_income=4.0,
        relocation_willingness=0.60,
        risk=0.45,
        dependents=2,
    )


# ==============================================================================
# B1: negotiate() and unified_roadmap() choose the exact same route
# ==============================================================================
def test_b1_negotiate_and_unified_roadmap_same_route(demo_student, demo_parent):
    """negotiate() and unified_roadmap() must return identical routes for every viable career."""
    routes = get_default_routes()
    careers = get_default_student_careers()

    # Run unified roadmap
    roadmap = unified_roadmap(
        student=demo_student,
        parent=demo_parent,
        careers=careers,
        routes=routes,
        alpha=0.5,
    )

    # Run negotiation slider
    neg = negotiate(
        student=demo_student,
        parent=demo_parent,
        alpha=0.5,
        careers=careers,
        routes=routes,
    )

    roadmap_routes = {item.career_id: item.best_route_id for item in roadmap.ranked_careers}
    negotiate_routes = {item["career_id"]: item["best_route_id"] for item in neg["ranked_careers"]}

    assert len(roadmap_routes) > 0
    assert len(negotiate_routes) > 0

    # Every career ranked in both must have the exact same chosen route
    common_cids = set(roadmap_routes.keys()) & set(negotiate_routes.keys())
    assert len(common_cids) > 0

    for cid in common_cids:
        assert roadmap_routes[cid] == negotiate_routes[cid], (
            f"Route mismatch for {cid}: roadmap chose {roadmap_routes[cid]}, negotiate chose {negotiate_routes[cid]}"
        )


# ==============================================================================
# B2: Tie-breaking is deterministic (higher score, then career_id ascending)
# ==============================================================================
def test_b2_deterministic_tie_breaking_shuffled_order():
    """Two careers with identical scores come out in career-id order across 20 shuffled iterations."""
    s = StudentConflictInput(risk_appetite=0.5, relocation_willingness=0.5, max_years_to_income=4.0)
    p = ParentConflictInput(risk=0.5, relocation_willingness=0.5, max_years_to_income=4.0)

    # Identical scores on Fit, Family, Market
    career_a = ScoredCareerInput(
        career_id="career_alpha",
        route_id="route_a",
        career_name="Career Alpha",
        student_fit=0.80,
        family_viability=0.75,
        market_score=0.70,
        is_financially_viable=True,
    )
    career_b = ScoredCareerInput(
        career_id="career_beta",
        route_id="route_b",
        career_name="Career Beta",
        student_fit=0.80,
        family_viability=0.75,
        market_score=0.70,
        is_financially_viable=True,
    )

    for i in range(20):
        # Shuffle inputs randomly
        inputs = [career_a, career_b]
        if i % 2 == 1:
            inputs.reverse()

        res = evaluate_negotiation_slider(s, p, inputs, alpha=0.5)

        # Higher score first, then career_id ascending -> career_alpha MUST be first
        ranked_ids = [c.career_id for c in res.ranked_careers]
        assert ranked_ids == ["career_alpha", "career_beta"], (
            f"Iteration {i} failed deterministic tie-break: got {ranked_ids}"
        )

        # Balanced pick must also break ties by career_id ascending
        assert res.balanced_pick_career_id == "career_alpha"


# ==============================================================================
# B3: Structured block_cause with priority: academic > no_route_data > cost
# ==============================================================================
def test_b3_structured_block_cause(demo_student, demo_parent):
    """Test block_cause outputs 'academic', 'no_route_data', and 'cost' with strict priority."""
    # 1. Academic failure career
    c_acad_fail = StudentCareer(
        career_id="acad_fail_career",
        career_name="Academic Fail Career",
        I_c={"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5},
        c_j={"logical": 0.7, "numerical": 0.7, "verbal": 0.7, "spatial": 0.5},
        u_j={"logical": 1.0, "numerical": 1.0, "verbal": 1.0, "spatial": 0.5},
        academic_requirements=AcademicRequirement(
            min_marks=98.0,  # Student marks 85 fail this
            required_subjects=["mathematics"],
        ),
    )
    r_acad = Route(
        career_id="acad_fail_career",
        route_id="r_acad_affordable",
        tuition=100000.0,
        living=50000.0,
        exam_equipment=5000.0,
        duration_years=4.0,
        starting_salary=600000.0,
        years_to_first_income=4.0,
        career_risk=0.4,
        relocation_need=0.5,
        domain="Technology & Engineering",
        sector="govt",
    )

    # 2. No route data career
    c_no_routes = StudentCareer(
        career_id="no_routes_career",
        career_name="No Routes Career",
        I_c={"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5},
        c_j={"logical": 0.5, "numerical": 0.5, "verbal": 0.5, "spatial": 0.5},
        u_j={"logical": 0.5, "numerical": 0.5, "verbal": 0.5, "spatial": 0.5},
        academic_requirements=AcademicRequirement(min_marks=50.0),
    )

    # 3. Cost failure career (valid academics, but all routes exceed financial gates)
    c_cost_fail = StudentCareer(
        career_id="cost_fail_career",
        career_name="Cost Fail Career",
        I_c={"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5},
        c_j={"logical": 0.5, "numerical": 0.5, "verbal": 0.5, "spatial": 0.5},
        u_j={"logical": 0.5, "numerical": 0.5, "verbal": 0.5, "spatial": 0.5},
        academic_requirements=AcademicRequirement(min_marks=50.0),
    )
    r_expensive = Route(
        career_id="cost_fail_career",
        route_id="r_super_expensive",
        tuition=9000000.0,
        living=2000000.0,
        exam_equipment=100000.0,
        duration_years=5.0,
        starting_salary=500000.0,
        years_to_first_income=5.0,
        career_risk=0.5,
        relocation_need=0.5,
        domain="Technology & Engineering",
        sector="private",
    )

    # 4. Multi-cause failure career (both academic fail AND cost fail)
    c_multi_fail = StudentCareer(
        career_id="multi_fail_career",
        career_name="Multi Fail Career",
        I_c={"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5},
        c_j={"logical": 0.5, "numerical": 0.5, "verbal": 0.5, "spatial": 0.5},
        u_j={"logical": 0.5, "numerical": 0.5, "verbal": 0.5, "spatial": 0.5},
        academic_requirements=AcademicRequirement(min_marks=99.0),  # Academic fails
    )
    r_multi_expensive = Route(
        career_id="multi_fail_career",
        route_id="r_multi_expensive",
        tuition=9000000.0,  # Cost also fails
        living=2000000.0,
        exam_equipment=100000.0,
        duration_years=5.0,
        starting_salary=500000.0,
        years_to_first_income=5.0,
        career_risk=0.5,
        relocation_need=0.5,
        domain="Technology & Engineering",
        sector="private",
    )

    report = generate_unified_roadmap(
        student=demo_student,
        parent=demo_parent,
        student_careers=[c_acad_fail, c_no_routes, c_cost_fail, c_multi_fail],
        routes=[r_acad, r_expensive, r_multi_expensive],
    )

    blocked_map = {b.career_id: b for b in report.blocked_careers}

    # Verify cause 1: academic
    assert "acad_fail_career" in blocked_map
    assert blocked_map["acad_fail_career"].block_cause == "academic"

    # Verify cause 2: no_route_data
    assert "no_routes_career" in blocked_map
    assert blocked_map["no_routes_career"].block_cause == "no_route_data"

    # Verify cause 3: cost
    assert "cost_fail_career" in blocked_map
    assert blocked_map["cost_fail_career"].block_cause == "cost"

    # Verify cause 4: multiple causes apply -> academic has priority over cost
    assert "multi_fail_career" in blocked_map
    assert blocked_map["multi_fail_career"].block_cause == "academic"


# ==============================================================================
# B4: Career without market record returns NOT FOUND, market_is_default=True
# ==============================================================================
def test_b4_missing_market_record_not_found(demo_student, demo_parent):
    """Career without a market record outputs NOT FOUND with market_is_default=true and never numeric."""
    # Create career with an uncollected ID not in market_signals.csv
    c_unseen = StudentCareer(
        career_id="unknown_hypothetical_career",
        career_name="Unknown Hypothetical Career",
        I_c={"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5},
        c_j={"logical": 0.6, "numerical": 0.6, "verbal": 0.6, "spatial": 0.5},
        u_j={"logical": 0.7, "numerical": 0.7, "verbal": 0.6, "spatial": 0.5},
        academic_requirements=AcademicRequirement(min_marks=50.0),
    )
    r_unseen = Route(
        career_id="unknown_hypothetical_career",
        route_id="r_unseen_route",
        tuition=100000.0,
        living=50000.0,
        exam_equipment=5000.0,
        duration_years=4.0,
        starting_salary=500000.0,
        years_to_first_income=4.0,
        career_risk=0.4,
        relocation_need=0.5,
        domain="General",
        sector="govt",
    )

    scores = per_career_scores(
        student=demo_student,
        parent=demo_parent,
        careers=[c_unseen],
        routes=[r_unseen],
        market_records=None,
    )

    assert len(scores) == 1
    item = scores[0]

    assert item["career_id"] == "unknown_hypothetical_career"
    assert item["market_score"] == "NOT FOUND"
    assert item["market_is_default"] is True
    assert not isinstance(item["market_score"], (int, float))

    # Test in unified_roadmap
    roadmap = generate_unified_roadmap(
        student=demo_student,
        parent=demo_parent,
        student_careers=[c_unseen],
        routes=[r_unseen],
        market_records=None,
    )

    assert len(roadmap.ranked_careers) == 1
    ranked_c = roadmap.ranked_careers[0]
    assert ranked_c.market_score == "NOT FOUND"
    assert ranked_c.market_is_default is True
    assert not isinstance(ranked_c.market_score, (int, float))

    # Test in negotiate()
    neg = negotiate(
        student=demo_student,
        parent=demo_parent,
        alpha=0.5,
        careers=[c_unseen],
        routes=[r_unseen],
        market_records=None,
    )

    assert len(neg["ranked_careers"]) == 1
    neg_c = neg["ranked_careers"][0]
    assert neg_c["market_score"] == "NOT FOUND"
    assert neg_c["market_is_default"] is True
    assert not isinstance(neg_c["market_score"], (int, float))
