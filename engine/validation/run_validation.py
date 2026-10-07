"""Validation Runner for UDAAN PRISM Engine (Synthetic Personas).

Loads 12 synthetic student and family personas from personas.yaml,
executes the PRISM engine through its standard interfaces, and verifies
pre-defined falsifiable expectations.

Exits with code 1 if any expectation fails, 0 if all pass.
Pure read-only validation: modifies no engine logic, config, or tests.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import yaml

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.student_fit.models import (
    Student,
    Career as StudentCareer,
    AcademicProfile,
    AcademicRequirement,
)
from engine.student_fit.scoring import calculate_student_fit
from engine.parent.models import ParentProfile, Route, SectorRatings
from engine.parent.scores import evaluate_parent_portfolio
from engine.parent.config import DEFAULT_CONFIG as PARENT_CONFIG
from engine.conflict.models import ScoredCareerInput, StudentConflictInput, ParentConflictInput
from engine.conflict.scores import evaluate_negotiation_slider
from engine.conflict.config import DEFAULT_CONFIG as CONFLICT_CONFIG
from engine.public import (
    overall_conflict,
    per_career_scores,
    negotiate,
    unified_roadmap,
    get_default_student_careers,
    get_default_routes,
)


def load_personas() -> List[Dict[str, Any]]:
    """Load synthetic personas specification from personas.yaml."""
    yaml_path = Path(__file__).resolve().parent / "personas.yaml"
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("personas", [])


def build_student(s_dict: Dict[str, Any]) -> Student:
    """Build Student dataclass from persona student dictionary."""
    acad_raw = s_dict.get("academics", {})
    acad = AcademicProfile(
        marks=float(acad_raw.get("marks", 75.0)),
        subjects=set(acad_raw.get("subjects", [])),
        exams=set(acad_raw.get("exams", [])),
    )
    return Student(
        student_id=s_dict.get("student_id", "student_val"),
        stage=s_dict.get("stage", "school"),
        I_s=s_dict.get("I_s", {}),
        a_j=s_dict.get("a_j", {}),
        academics=acad,
        risk_appetite=float(s_dict.get("risk_appetite", 0.5)),
        domain_preference=s_dict.get("domain_preference", {}),
        relocation_willingness=float(s_dict.get("relocation_willingness", 0.5)),
        max_years_to_income=float(s_dict.get("max_years_to_income", 4.0)),
    )


def build_parent(p_dict: Dict[str, Any]) -> ParentProfile:
    """Build ParentProfile model from persona family dictionary."""
    sec_raw = p_dict.get("sector_ratings", {})
    sec = SectorRatings(
        govt=int(sec_raw.get("govt", 3)),
        private=int(sec_raw.get("private", 3)),
        entrepreneurship=int(sec_raw.get("entrepreneurship", 3)),
    )
    return ParentProfile(
        savings=float(p_dict.get("savings", 0.0)),
        monthly_surplus=float(p_dict.get("monthly_surplus", 0.0)),
        household_income=float(p_dict.get("household_income", 0.0)),
        existing_emis=float(p_dict.get("existing_emis", 0.0)),
        loan_max=float(p_dict.get("loan_max", 0.0)),
        domain_ratings=p_dict.get("domain_ratings", {}),
        sector_ratings=sec,
        min_salary=float(p_dict.get("min_salary", 0.0)),
        max_years_to_income=float(p_dict.get("max_years_to_income", 4.0)),
        relocation_willingness=float(p_dict.get("relocation_willingness", 0.5)),
        risk=float(p_dict.get("risk", 0.5)),
    )


def run_persona_validation(
    persona: Dict[str, Any],
    default_careers: List[StudentCareer],
    default_routes: List[Route],
) -> List[Dict[str, Any]]:
    """Validate a single persona against its rough falsifiable expectations."""
    pid = persona["id"]
    desc = persona["description"]
    student = build_student(persona["student"])
    parent = build_parent(persona["family"])
    expectations = persona.get("expectations", [])

    # Run engine baseline pipelines
    conflict_diag = overall_conflict(student, parent)
    career_evals = per_career_scores(student, parent, default_careers, default_routes)
    career_evals_by_id = {c["career_id"]: c for c in career_evals}
    roadmap = unified_roadmap(student, parent, alpha=0.50, careers=default_careers, routes=default_routes)

    # Sort careers by student fit
    careers_by_fit = sorted(career_evals, key=lambda x: x["student_fit"], reverse=True)
    top_fit_ids = [c["career_id"] for c in careers_by_fit[:5]]

    results = []

    for exp in expectations:
        rule = exp.get("rule")
        exp_desc = exp.get("description", rule)
        passed = False
        actual_val: Any = None
        expected_val: Any = None

        if rule == "top_fit_careers_contain":
            targets = exp["target_careers"]
            min_m = exp.get("min_matches", 1)
            matches = [t for t in targets if t in top_fit_ids]
            passed = len(matches) >= min_m
            expected_val = f">= {min_m} of {targets} in top 5"
            actual_val = f"Found {len(matches)}: {matches} (Top 5: {top_fit_ids})"

        elif rule == "career_not_in_top_fit":
            target_cid = exp["career_id"]
            k = exp.get("top_k", 5)
            top_k_ids = [c["career_id"] for c in careers_by_fit[:k]]
            passed = target_cid not in top_k_ids
            expected_val = f"'{target_cid}' NOT in top {k}"
            actual_val = f"Top {k} list: {top_k_ids}"

        elif rule == "conflict_index_level":
            exp_level = exp.get("expected_level")
            c_idx = conflict_diag["conflict_index"]
            actual_val = c_idx
            if exp_level == "high":
                min_v = exp.get("min_value", 40.0)
                expected_val = f"Conflict Index >= {min_v}"
                passed = c_idx >= min_v
            else:
                max_v = exp.get("max_value", 20.0)
                expected_val = f"Conflict Index <= {max_v}"
                passed = c_idx <= max_v

        elif rule == "conflict_dimension_driver":
            dim = exp["dimension"]
            min_g = exp.get("min_gap", 0.30)
            gap = conflict_diag["dimension_gaps"].get(dim, 0.0)
            passed = gap >= min_g
            expected_val = f"{dim} gap >= {min_g}"
            actual_val = f"{dim} gap = {gap:.3f}"

        elif rule == "expensive_routes_fail_gate":
            target_cid = exp["career_id"]
            target_rid = exp["route_id"]
            target_routes = [r for r in default_routes if r.career_id == target_cid and r.route_id == target_rid]
            if not target_routes:
                target_routes = [r for r in default_routes if r.career_id == target_cid]
            p_eval = evaluate_parent_portfolio(parent, target_routes, PARENT_CONFIG)
            rep = next((r for r in p_eval.reports if r.route_id == target_rid), p_eval.reports[0] if p_eval.reports else None)
            actual_g_fin = rep.g_fin if rep else 0
            expected_g_fin = exp.get("expected_g_fin", 0)
            passed = (actual_g_fin == expected_g_fin)
            expected_val = f"g_fin == {expected_g_fin}"
            actual_val = f"g_fin == {actual_g_fin} (cost: {getattr(rep, 'cost_net', 0):,.0f})"

        elif rule == "compromise_zone_non_empty":
            exp_bool = exp.get("expected", True)
            cz_count = len(roadmap.compromise_zone_careers)
            passed = (cz_count > 0) == exp_bool
            expected_val = f"non_empty == {exp_bool}"
            actual_val = f"count = {cz_count} careers in compromise zone"

        elif rule == "financial_gate_cleared":
            target_cid = exp["career_id"]
            c_info = career_evals_by_id.get(target_cid)
            g_fin = c_info.get("g_fin", 0) if c_info else 0
            exp_g = exp.get("expected_g_fin", 1)
            passed = (g_fin == exp_g)
            expected_val = f"g_fin == {exp_g}"
            actual_val = f"g_fin == {g_fin}"

        elif rule == "low_signal_flag":
            target_cid = exp["career_id"]
            target_sc = next((c for c in default_careers if c.career_id == target_cid), default_careers[0])
            s_res = calculate_student_fit(student, target_sc)
            passed = (s_res.low_signal == exp.get("expected", True))
            expected_val = f"low_signal == {exp.get('expected', True)}"
            actual_val = f"low_signal == {s_res.low_signal}"

        elif rule == "interest_fit_score":
            target_cid = exp["career_id"]
            target_sc = next((c for c in default_careers if c.career_id == target_cid), default_careers[0])
            s_res = calculate_student_fit(student, target_sc)
            exp_score = exp.get("expected_score", 50.0)
            passed = abs(s_res.InterestFit - exp_score) < 0.01
            expected_val = f"InterestFit == {exp_score}"
            actual_val = f"InterestFit == {s_res.InterestFit}"

        elif rule == "stretch_flag_present":
            target_cid = exp["career_id"]
            target_sc = next((c for c in default_careers if c.career_id == target_cid), default_careers[0])
            s_res = calculate_student_fit(student, target_sc)
            passed = (s_res.stretch == exp.get("expected_stretch", True))
            expected_val = f"stretch == {exp.get('expected_stretch', True)}"
            actual_val = f"stretch == {s_res.stretch} (ratio: {s_res.stretch_shortfall_ratio})"

        elif rule == "stretch_reasons_contain":
            target_cid = exp["career_id"]
            target_sc = next((c for c in default_careers if c.career_id == target_cid), default_careers[0])
            s_res = calculate_student_fit(student, target_sc)
            keywords = exp.get("keywords", [])
            has_keywords = all(any(k in r.lower() for r in s_res.stretch_reasons) for k in keywords)
            passed = has_keywords
            expected_val = f"reasons contain {keywords}"
            actual_val = f"reasons: {s_res.stretch_reasons}"

        elif rule == "career_not_blocked":
            target_cid = exp["career_id"]
            target_sc = next((c for c in default_careers if c.career_id == target_cid), default_careers[0])
            s_res = calculate_student_fit(student, target_sc)
            passed = (s_res.G_acad == 1 and not s_res.blocked)
            expected_val = "G_acad == 1 and not blocked"
            actual_val = f"G_acad == {s_res.G_acad}, blocked == {s_res.blocked}"

        elif rule == "academic_gate_blocked":
            cust = persona.get("custom_career", {})
            req_dict = cust.get("academic_requirements", {})
            custom_sc = StudentCareer(
                career_id=cust.get("career_id", "custom_c"),
                career_name=cust.get("career_name", "Custom Career"),
                I_c=cust.get("I_c", {"R": 0.30, "I": 0.90, "A": 0.20, "S": 0.80, "E": 0.30, "C": 0.60}),
                c_j=cust.get("c_j", {"logical": 0.70, "numerical": 0.70, "verbal": 0.60, "spatial": 0.50}),
                u_j=cust.get("u_j", {"logical": 0.80, "numerical": 0.80, "verbal": 0.70, "spatial": 0.50}),
                academic_requirements=AcademicRequirement(
                    min_marks=float(req_dict.get("min_marks", 60.0)),
                    required_subjects=req_dict.get("required_subjects", []),
                    required_exams=req_dict.get("required_exams", []),
                ),
            )
            s_res = calculate_student_fit(student, custom_sc)
            exp_g = exp.get("expected_g_acad", 0)
            passed = (s_res.G_acad == exp_g)
            expected_val = f"G_acad == {exp_g}"
            actual_val = f"G_acad == {s_res.G_acad} (reasons: {s_res.blocked_reasons})"

        elif rule == "academic_blocked_reasons_contain":
            cust = persona.get("custom_career", {})
            req_dict = cust.get("academic_requirements", {})
            custom_sc = StudentCareer(
                career_id=cust.get("career_id", "custom_c"),
                career_name=cust.get("career_name", "Custom Career"),
                I_c=cust.get("I_c", {"R": 0.30, "I": 0.90, "A": 0.20, "S": 0.80, "E": 0.30, "C": 0.60}),
                c_j=cust.get("c_j", {"logical": 0.70, "numerical": 0.70, "verbal": 0.60, "spatial": 0.50}),
                u_j=cust.get("u_j", {"logical": 0.80, "numerical": 0.80, "verbal": 0.70, "spatial": 0.50}),
                academic_requirements=AcademicRequirement(
                    min_marks=float(req_dict.get("min_marks", 60.0)),
                    required_subjects=req_dict.get("required_subjects", []),
                    required_exams=req_dict.get("required_exams", []),
                ),
            )
            s_res = calculate_student_fit(student, custom_sc)
            keywords = exp.get("keywords", [])
            has_kw = any(any(k in r.lower() for k in keywords) for r in s_res.blocked_reasons)
            passed = has_kw
            expected_val = f"blocked reasons contain any of {keywords}"
            actual_val = f"reasons: {s_res.blocked_reasons}"

        elif rule == "blocked_suggestions_contain":
            target_cid = exp["career_id"]
            p_eval = evaluate_parent_portfolio(parent, default_routes, PARENT_CONFIG)
            blocked_for_cid = [b for b in p_eval.blocked_list if b.career_id == target_cid]
            keywords = exp.get("keywords", [])
            has_kw = any(any(k in b.suggestion.lower() for k in keywords) for b in blocked_for_cid)
            passed = has_kw
            expected_val = f"suggestions contain any of {keywords}"
            suggestions = [b.suggestion for b in blocked_for_cid]
            actual_val = f"suggestions: {suggestions}"

        elif rule == "all_dimension_gaps_near_zero":
            max_g = exp.get("max_gap", 0.05)
            gaps = conflict_diag["dimension_gaps"]
            passed = all(g <= max_g for g in gaps.values())
            expected_val = f"all gaps <= {max_g}"
            actual_val = f"gaps: {gaps}"

        elif rule == "high_conflict_flag":
            exp_high = exp.get("expected", True)
            actual_high = conflict_diag["is_high_conflict"]
            passed = (actual_high == exp_high)
            expected_val = f"is_high_conflict == {exp_high}"
            actual_val = f"is_high_conflict == {actual_high}"

        elif rule == "dimension_decomposition_all_high":
            min_g = exp.get("min_gap", 0.50)
            gaps = conflict_diag["dimension_gaps"]
            passed = all(g >= min_g for g in gaps.values())
            expected_val = f"all gaps >= {min_g}"
            actual_val = f"gaps: {gaps}"

        elif rule == "route_financial_status":
            cr = persona.get("custom_route", {})
            test_r = Route(
                career_id=cr["career_id"],
                route_id=cr["route_id"],
                tuition=cr.get("tuition", 200000.0),
                starting_salary=cr.get("starting_salary"),
                domain=cr.get("domain", "tech_engineering"),
            )
            p_res = evaluate_parent_portfolio(parent, [test_r], PARENT_CONFIG)
            rep = p_res.reports[0]
            exp_stat = exp.get("expected_status", "insufficient_data")
            passed = (rep.status == exp_stat)
            expected_val = f"status == '{exp_stat}'"
            actual_val = f"status == '{rep.status}'"

        elif rule == "route_f_family_zero":
            cr = persona.get("custom_route", {})
            test_r = Route(
                career_id=cr["career_id"],
                route_id=cr["route_id"],
                tuition=cr.get("tuition", 200000.0),
                starting_salary=cr.get("starting_salary"),
                domain=cr.get("domain", "tech_engineering"),
            )
            p_res = evaluate_parent_portfolio(parent, [test_r], PARENT_CONFIG)
            rep = p_res.reports[0]
            exp_f = exp.get("expected_f_family", 0.0)
            passed = (rep.f_family == exp_f)
            expected_val = f"f_family == {exp_f}"
            actual_val = f"f_family == {rep.f_family}"

        elif rule == "route_g_fin_zero":
            cr = persona.get("custom_route", {})
            test_r = Route(
                career_id=cr["career_id"],
                route_id=cr["route_id"],
                tuition=cr.get("tuition", 200000.0),
                starting_salary=cr.get("starting_salary"),
                domain=cr.get("domain", "tech_engineering"),
            )
            p_res = evaluate_parent_portfolio(parent, [test_r], PARENT_CONFIG)
            rep = p_res.reports[0]
            exp_g = exp.get("expected_g_fin", 0)
            passed = (rep.g_fin == exp_g)
            expected_val = f"g_fin == {exp_g}"
            actual_val = f"g_fin == {rep.g_fin}"

        elif rule == "financial_gate_without_grant_fails":
            cr = persona.get("custom_route_no_scholarship", {})
            test_r = Route(
                career_id=cr["career_id"],
                route_id=cr["route_id"],
                tuition=cr.get("tuition", 800000.0),
                living=cr.get("living", 200000.0),
                exam_equipment=cr.get("exam_equipment", 20000.0),
                grant=cr.get("grant", 0.0),
                starting_salary=cr.get("starting_salary", 800000.0),
                duration_years=cr.get("duration_years", 4.0),
                domain=cr.get("domain", "design_creative"),
            )
            p_res = evaluate_parent_portfolio(parent, [test_r], PARENT_CONFIG)
            rep = p_res.reports[0]
            exp_g = exp.get("expected_g_fin", 0)
            passed = (rep.g_fin == exp_g)
            expected_val = f"g_fin == {exp_g}"
            actual_val = f"g_fin == {rep.g_fin} (net cost: {rep.cost_net:,.0f})"

        elif rule == "financial_gate_with_grant_passes":
            cr = persona.get("custom_route_with_scholarship", {})
            test_r = Route(
                career_id=cr["career_id"],
                route_id=cr["route_id"],
                tuition=cr.get("tuition", 800000.0),
                living=cr.get("living", 200000.0),
                exam_equipment=cr.get("exam_equipment", 20000.0),
                grant=cr.get("grant", 950000.0),
                starting_salary=cr.get("starting_salary", 800000.0),
                duration_years=cr.get("duration_years", 4.0),
                domain=cr.get("domain", "design_creative"),
            )
            p_res = evaluate_parent_portfolio(parent, [test_r], PARENT_CONFIG)
            rep = p_res.reports[0]
            exp_g = exp.get("expected_g_fin", 1)
            passed = (rep.g_fin == exp_g)
            expected_val = f"g_fin == {exp_g}"
            actual_val = f"g_fin == {rep.g_fin} (net cost: {rep.cost_net:,.0f})"

        elif rule == "family_viability_improves":
            cr_without = persona.get("custom_route_no_scholarship", {})
            cr_with = persona.get("custom_route_with_scholarship", {})
            r_without = Route(
                career_id=cr_without["career_id"],
                route_id=cr_without["route_id"],
                tuition=cr_without.get("tuition", 800000.0),
                grant=cr_without.get("grant", 0.0),
                starting_salary=cr_without.get("starting_salary", 800000.0),
                domain=cr_without.get("domain", "design_creative"),
            )
            r_with = Route(
                career_id=cr_with["career_id"],
                route_id=cr_with["route_id"],
                tuition=cr_with.get("tuition", 800000.0),
                grant=cr_with.get("grant", 950000.0),
                starting_salary=cr_with.get("starting_salary", 800000.0),
                domain=cr_with.get("domain", "design_creative"),
            )
            p_res = evaluate_parent_portfolio(parent, [r_without, r_with], PARENT_CONFIG)
            rep_without = next(r for r in p_res.reports if r.route_id == cr_without["route_id"])
            rep_with = next(r for r in p_res.reports if r.route_id == cr_with["route_id"])
            passed = (rep_with.f_family > rep_without.f_family)
            expected_val = f"f_family_with > f_family_without"
            actual_val = f"with={rep_with.f_family:.1f} vs without={rep_without.f_family:.1f}"

        elif rule == "top_fit_careers_creator":
            targets = exp["target_careers"]
            min_m = exp.get("min_matches", 2)
            matches = [t for t in targets if t in top_fit_ids]
            passed = len(matches) >= min_m
            expected_val = f">= {min_m} of {targets} in top 5"
            actual_val = f"Found {len(matches)}: {matches} (Top 5: {top_fit_ids})"

        elif rule == "fit_gap_large":
            target_cid = exp["career_id"]
            c_info = career_evals_by_id.get(target_cid)
            fit_gap = c_info.get("fit_gap", 0.0) if c_info else 0.0
            min_g = exp.get("min_gap", 20.0)
            passed = fit_gap >= min_g
            expected_val = f"fit_gap >= {min_g}"
            actual_val = f"fit_gap = {fit_gap:.1f}"

        elif rule == "career_in_compromise_zone":
            target_cid = exp["career_id"]
            exp_in_cz = exp.get("expected", True)
            candidates_raw = persona.get("boundary_candidates", [])
            scored_inputs = [
                ScoredCareerInput(
                    career_id=c["career_id"],
                    route_id=c["route_id"],
                    career_name=c["career_name"],
                    student_fit=float(c["student_fit"]),
                    family_viability=float(c["family_viability"]),
                    market_score=float(c.get("market_score", 0.70)),
                    is_financially_viable=bool(c.get("is_financially_viable", True)),
                )
                for c in candidates_raw
            ]
            s_input = StudentConflictInput(
                risk_appetite=student.risk_appetite,
                relocation_willingness=student.relocation_willingness,
                max_years_to_income=student.max_years_to_income,
            )
            p_input = ParentConflictInput(
                risk=parent.risk,
                relocation_willingness=parent.relocation_willingness,
                max_years_to_income=parent.max_years_to_income,
            )
            neg_res = evaluate_negotiation_slider(s_input, p_input, scored_inputs, alpha=0.50, config=CONFLICT_CONFIG)
            cz_ids = {c.career_id for c in neg_res.compromise_zone_careers}
            is_in = (target_cid in cz_ids)
            passed = (is_in == exp_in_cz)
            expected_val = f"in_compromise_zone == {exp_in_cz}"
            actual_val = f"in_compromise_zone == {is_in} (CZ careers: {list(cz_ids)})"

        else:
            passed = False
            expected_val = "Recognized rule"
            actual_val = f"Unknown rule: {rule}"

        results.append({
            "persona_id": pid,
            "rule": rule,
            "description": exp_desc,
            "passed": passed,
            "expected": expected_val,
            "actual": actual_val,
        })

    return results


def main() -> int:
    """Execute validation runner across all personas and report results."""
    print("=" * 110)
    print("         UDAAN PRISM ENGINE — SYNTHETIC PERSONAS VALIDATION SUITE (READ-ONLY)")
    print("=" * 110)

    personas = load_personas()
    default_careers = get_default_student_careers()
    default_routes = get_default_routes()

    all_results: List[Dict[str, Any]] = []
    persona_stats: List[Dict[str, Any]] = []

    total_passed = 0
    total_failed = 0

    for idx, persona in enumerate(personas, 1):
        pid = persona["id"]
        desc = persona["description"]
        print(f"\n[{idx}/12] Persona: {pid}")
        print(f"      Description: {desc}")
        print("      " + "-" * 100)

        p_results = run_persona_validation(persona, default_careers, default_routes)
        p_passed = sum(1 for r in p_results if r["passed"])
        p_failed = sum(1 for r in p_results if not r["passed"])

        total_passed += p_passed
        total_failed += p_failed

        persona_stats.append({
            "id": pid,
            "passed": p_passed,
            "failed": p_failed,
            "total": len(p_results),
        })

        for r in p_results:
            status_tag = "[PASS]" if r["passed"] else "[FAIL]"
            print(f"      {status_tag} {r['description']}")
            print(f"             Expected: {r['expected']}")
            print(f"             Actual:   {r['actual']}")
            all_results.append(r)

    # Summary Table
    print("\n" + "=" * 110)
    print("                                   VALIDATION SUMMARY TABLE")
    print("=" * 110)
    header = f"{'Persona ID':<50} | {'Passed':<8} | {'Failed':<8} | {'Total':<6} | {'Status'}"
    print(header)
    print("-" * 110)

    for stat in persona_stats:
        status_str = "ALL PASSED" if stat["failed"] == 0 else f"{stat['failed']} FAILED"
        row = (
            f"{stat['id']:<50} | "
            f"{stat['passed']:<8} | "
            f"{stat['failed']:<8} | "
            f"{stat['total']:<6} | "
            f"{status_str}"
        )
        print(row)

    print("-" * 110)
    overall_status = "PASSED" if total_failed == 0 else "FAILED"
    print(f"TOTAL: {len(personas)} Personas | {total_passed} Passed | {total_failed} Failed | OVERALL: {overall_status}")
    print("=" * 110 + "\n")

    return 1 if total_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
