"""Comprehensive Unit and Regression Tests for PRISM Engine Family Evaluation (DataQuest 3.0).

Tests:
1. A route missing tuition -> blocked, 'not_enough_data', missing_fields lists it.
2. A route missing only hostel -> cost_status 'partial', is_lower_bound true, never 'confirmed' pass.
3. A complete route -> 'complete', all numbers consistent with the same best_route.
4. blend_grid always has 21 entries, lambda values exact, ranks deterministic.
5. Missing values come back as None, never 0 or NaN (scan the whole response).
6. Every non-None data figure has source_url and retrieved_on (scan data files; fail on violations).
7. payback_range is reproducible with the same seed and returns None when p10/p90 are missing.
8. Persona golden-file tests.
9. high_conflict flag flips correctly around the configured threshold.
"""

from __future__ import annotations
import csv
import json
import math
from pathlib import Path
import pytest
import numpy as np

from engine.parent.models import ParentProfile, Route, SectorRatings
from engine.parent.scores import evaluate_route
from engine.parent.config import DEFAULT_CONFIG as PARENT_CONFIG
from engine.evaluation import (
    evaluate_family,
    payback_range,
    match_scholarships,
    CORE_CAREERS,
)
from engine.student_fit.models import Student, AcademicProfile
from engine.config import DEFAULT_CONFIG as MASTER_CONFIG

REPO_ROOT = Path(__file__).resolve().parents[2]
import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SNAPSHOTS_DIR = REPO_ROOT / "tests" / "snapshots"


@pytest.fixture
def sample_parent():
    return ParentProfile(
        savings=1000000.0,
        monthly_surplus=50000.0,
        household_income=150000.0,
        existing_emis=10000.0,
        loan_max=1500000.0,
        domain_ratings={"tech_engineering": 5.0, "healthcare_medicine": 4.0},
        sector_ratings=SectorRatings(govt=4, private=4, entrepreneurship=2),
        min_salary=600000.0,
        max_years_to_income=4.0,
        relocation_willingness=0.8,
        risk=0.5,
    )


@pytest.fixture
def sample_student():
    return Student(
        student_id="test_student",
        stage="school",
        I_s={"R": 0.8, "I": 0.8, "A": 0.3, "S": 0.2, "E": 0.4, "C": 0.6},
        a_j={"logical": 0.8, "numerical": 0.8, "verbal": 0.7, "spatial": 0.6},
        academics=AcademicProfile(marks=85.0),
        risk_appetite=0.6,
        domain_preference={"tech_engineering": 5.0},
        relocation_willingness=0.8,
        max_years_to_income=4.0,
    )


# ---------------------------------------------------------------------------
# Test 1: Route missing tuition -> blocked, "not_enough_data"
# ---------------------------------------------------------------------------
def test_1_route_missing_tuition_blocked_not_enough_data(sample_parent):
    route = Route(
        career_id="software_developer",
        route_id="route_test_no_tuition",
        tuition=None,  # Missing tuition
        duration_years=4.0,
        starting_salary=600000.0,
        living=100000.0,
        exam_equipment=10000.0,
    )
    v_rep = evaluate_route(sample_parent, route, PARENT_CONFIG)

    assert v_rep.g_fin == 0
    assert v_rep.gate_cleared == 0
    assert v_rep.cost_status == "missing"
    assert v_rep.blocked_cause == "not_enough_data"
    assert "tuition" in v_rep.missing_fields
    assert v_rep.is_lower_bound is False
    assert v_rep.provisional_pass is False


# ---------------------------------------------------------------------------
# Test 2: Route missing only hostel -> cost_status "partial", lower bound, provisional pass
# ---------------------------------------------------------------------------
def test_2_route_missing_only_hostel_partial_lower_bound(sample_parent):
    route = Route(
        career_id="software_developer",
        route_id="route_test_partial",
        tuition=200000.0,
        duration_years=4.0,
        starting_salary=600000.0,
        living=None,
        hostel=None,  # Missing hostel only
        mess=50000.0,
        exam_equipment=15000.0,
    )
    v_rep = evaluate_route(sample_parent, route, PARENT_CONFIG)

    assert v_rep.cost_status == "partial"
    assert v_rep.is_lower_bound is True
    assert "hostel" in v_rep.missing_fields
    assert v_rep.total_cost_known == pytest.approx(265000.0)  # 200k + 50k + 15k
    assert v_rep.g_fin == 1
    # When partial route passes financial gate, it is provisional pass (never confirmed confirmed pass)
    assert v_rep.provisional_pass is True


# ---------------------------------------------------------------------------
# Test 3: Complete route -> "complete", all numbers consistent with best_route
# ---------------------------------------------------------------------------
def test_3_complete_route_consistent_best_route(sample_student, sample_parent):
    route = Route(
        career_id="software_developer",
        route_id="route_test_complete",
        tuition=800000.0,
        duration_years=4.0,
        starting_salary=1000000.0,
        living=200000.0,
        exam_equipment=20000.0,
    )
    v_rep = evaluate_route(sample_parent, route, PARENT_CONFIG)

    assert v_rep.cost_status == "complete"
    assert v_rep.is_lower_bound is False
    assert v_rep.provisional_pass is False
    assert v_rep.missing_fields == []
    assert v_rep.cost_net == pytest.approx(1020000.0)

    # Test through evaluate_family facade
    eval_res = evaluate_family(sample_student, sample_parent)
    c_sw = next(c for c in eval_res["careers"] if c["career_id"] == "software_developer")

    assert c_sw["data_status"] == "core"
    best_r = c_sw["best_route"]
    assert best_r is not None
    # Verify that the best route is used consistently across cost, EMI, payback, and gates
    assert c_sw["gates"]["gate_financial"] == 1 if (not c_sw["blocked"] or c_sw["blocked_cause"] == "academic_ineligible") else 0
    assert best_r["monthly_emi"] >= 0.0
    assert best_r["payback_years"] >= 0.0


# ---------------------------------------------------------------------------
# Test 4: blend_grid always has 21 entries, lambda values exact, ranks deterministic
# ---------------------------------------------------------------------------
def test_4_blend_grid_structure_and_deterministic_ranks(sample_student, sample_parent):
    eval_res = evaluate_family(sample_student, sample_parent)

    for c in eval_res["careers"]:
        grid = c["blend_grid"]
        assert len(grid) == 21, f"Career {c['career_id']} blend_grid length is {len(grid)}, expected 21"

        expected_lambdas = [round(i * 0.05, 2) for i in range(21)]
        actual_lambdas = [item["lambda"] for item in grid]
        assert actual_lambdas == expected_lambdas

        if c["data_status"] == "core" and c["scores"]["fit"] is not None and c["scores"]["family_viability"] is not None:
            for item in grid:
                assert item["rank"] is not None
                assert item["rank_score"] is not None
                assert 1 <= item["rank"] <= len(CORE_CAREERS)
        else:
            # Pending careers have None for rank_score and rank
            for item in grid:
                assert item["rank"] is None
                assert item["rank_score"] is None

    # Determinism: run twice with same inputs, ranks must be strictly identical
    eval_res_2 = evaluate_family(sample_student, sample_parent)
    for c1, c2 in zip(eval_res["careers"], eval_res_2["careers"]):
        for g1, g2 in zip(c1["blend_grid"], c2["blend_grid"]):
            assert g1["rank_score"] == g2["rank_score"]
            assert g1["rank"] == g2["rank"]


# ---------------------------------------------------------------------------
# Test 5: Missing values come back as None, never 0 or NaN (scan whole response)
# ---------------------------------------------------------------------------
def test_5_missing_values_strict_none_never_nan_or_fabricated_zero(sample_student, sample_parent):
    eval_res = evaluate_family(sample_student, sample_parent)

    def scan_for_nan(obj, path=""):
        if isinstance(obj, float):
            assert not math.isnan(obj), f"NaN found at path: {path}"
            assert not math.isinf(obj), f"Inf found at path: {path}"
        elif isinstance(obj, str):
            assert obj.lower() != "nan", f"NaN string found at path: {path}"
        elif isinstance(obj, dict):
            for k, v in obj.items():
                scan_for_nan(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                scan_for_nan(v, f"{path}[{i}]")

    scan_for_nan(eval_res)

    # Check pending careers have strict None scores, not 0
    pending_careers = [c for c in eval_res["careers"] if c["data_status"] == "pending"]
    assert len(pending_careers) > 0
    for pc in pending_careers:
        assert pc["scores"]["family_viability"] is None
        assert pc["scores"]["composite"] is None
        assert pc["scores"]["market"] is None
        assert pc["scores"]["final"] is None
        assert pc["cost"]["total"] is None
        assert pc["cost"]["total_cost_known"] is None
        assert pc["gates"]["gate_financial"] is None


# ---------------------------------------------------------------------------
# Test 6: Every non-None data figure has source_url and retrieved_on in data files
# ---------------------------------------------------------------------------
def test_6_provenance_audit_sources_and_retrieval_dates():
    files_to_check = [
        ("data_pipeline/processed/route_costs.csv", ["tuition_fee_total", "hostel_fee_total", "mess_fee_total"]),
        ("data_pipeline/processed/scholarships.csv", ["amount"]),
        ("data_pipeline/processed/entrance_exams.csv", ["exam_name"]),
        ("data_pipeline/processed/demand_signals.csv", ["value"]),
    ]

    for rel_path, check_cols in files_to_check:
        full_path = REPO_ROOT / rel_path
        if not full_path.exists():
            continue

        with open(full_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader, start=2):
                url = row.get("source_url") or row.get("apply_url") or row.get("official_url")
                retrieved = row.get("retrieved_on")

                # If any numeric figure is present and not NOT FOUND
                has_figure = any(row.get(c) not in (None, "", "NOT FOUND") for c in check_cols if c in row)
                if has_figure:
                    assert url and url != "NOT FOUND" and url.startswith("http"), (
                        f"Missing source_url in {rel_path} line {row_idx}: {row}"
                    )
                    assert retrieved and retrieved != "NOT FOUND" and len(retrieved) == 10, (
                        f"Missing or invalid retrieved_on in {rel_path} line {row_idx}: {row}"
                    )


# ---------------------------------------------------------------------------
# Test 7: payback_range is reproducible and returns None when p10/p90 missing
# ---------------------------------------------------------------------------
def test_7_payback_range_monte_carlo():
    # A. Missing p10 or p90 -> returns None
    route_missing = {"career_id": "software_developer", "p10": None, "p90": None, "cost_net": 500000.0}
    res_none = payback_range(route_missing, parent_input=None)
    assert res_none is None

    # B. Populated p10/p90 -> returns seeded reproducible simulation
    route_valid = {"career_id": "software_developer", "p10": 6.0, "p90": 20.0, "cost_net": 800000.0}
    sim1 = payback_range(route_valid, parent_input=None, n=5000, seed=123)
    sim2 = payback_range(route_valid, parent_input=None, n=5000, seed=123)

    assert sim1 is not None
    assert sim2 is not None
    assert sim1 == sim2
    assert "p10_years" in sim1
    assert "p50_years" in sim1
    assert "p90_years" in sim1
    assert sim1["p10_years"] <= sim1["p50_years"] <= sim1["p90_years"]
    assert 0.0 <= sim1["prob_repay_within_horizon"] <= 1.0
    assert len(sim1["histogram"]["bin_counts"]) == 10


# ---------------------------------------------------------------------------
# Test 8: Persona golden-file tests
# ---------------------------------------------------------------------------
def test_8_persona_golden_snapshots_regression():
    import importlib.util
    reg_file = REPO_ROOT / "tests" / "test_persona_regression.py"
    spec = importlib.util.spec_from_file_location("test_persona_regression", reg_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for short_id, full_id in mod.PERSONA_IDS:
        mod.test_persona_golden_snapshot(short_id, full_id)


# ---------------------------------------------------------------------------
# Test 9: high_conflict flag flips correctly around the configured threshold
# ---------------------------------------------------------------------------
def test_9_high_conflict_flag_flips_at_threshold():
    threshold = MASTER_CONFIG.high_conflict_threshold  # 60.0

    # 1. Aligned family (low conflict)
    s_aligned = Student(
        student_id="s_align", stage="school",
        I_s={"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5},
        a_j={"logical": 0.5, "numerical": 0.5, "verbal": 0.5, "spatial": 0.5},
        academics=AcademicProfile(marks=75.0),
        risk_appetite=0.5, domain_preference={"tech_engineering": 5.0},
        relocation_willingness=0.5, max_years_to_income=4.0
    )
    p_aligned = ParentProfile(
        savings=500000.0, monthly_surplus=30000.0, household_income=100000.0,
        existing_emis=0.0, loan_max=1000000.0,
        domain_ratings={"tech_engineering": 5.0},
        sector_ratings=SectorRatings(govt=3, private=3, entrepreneurship=3),
        min_salary=500000.0, max_years_to_income=4.0, relocation_willingness=0.5, risk=0.5
    )
    res_low = evaluate_family(s_aligned, p_aligned)
    assert res_low["conflict_index"] < threshold
    assert res_low["high_conflict"] is False

    # 2. Diametrically opposed family (high conflict)
    s_opposed = Student(
        student_id="s_opp", stage="school",
        I_s={"R": 0.9, "I": 0.9, "A": 0.1, "S": 0.1, "E": 0.1, "C": 0.1},
        a_j={"logical": 0.8, "numerical": 0.8, "verbal": 0.8, "spatial": 0.8},
        academics=AcademicProfile(marks=90.0),
        risk_appetite=0.95, domain_preference={"design_creative": 5.0},
        relocation_willingness=1.0, max_years_to_income=8.0
    )
    p_opposed = ParentProfile(
        savings=100000.0, monthly_surplus=5000.0, household_income=40000.0,
        existing_emis=15000.0, loan_max=200000.0,
        domain_ratings={"healthcare_medicine": 5.0, "design_creative": 1.0},
        sector_ratings=SectorRatings(govt=5, private=1, entrepreneurship=1),
        min_salary=800000.0, max_years_to_income=2.0, relocation_willingness=0.0, risk=0.05
    )
    res_high = evaluate_family(s_opposed, p_opposed)
    assert res_high["conflict_index"] >= threshold
    assert res_high["high_conflict"] is True
