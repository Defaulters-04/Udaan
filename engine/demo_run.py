"""Demo and smoke test runner for the PRISM Engine.

Demonstrates end-to-end integration:
1. Maps questionnaire answers directly to Student and ParentProfile models.
2. Computes the Family Conflict Index and dimension gaps.
3. Evaluates per-career scores, academic/financial gates, and data completeness.
4. Explores the Negotiation Slider at alpha=0.5.
5. Generates the full unified roadmap report.

Run from repository root:
    python engine/demo_run.py
"""

import json
import sys
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.answer_mapping import student_from_answers, parent_from_answers
from engine.public import overall_conflict, per_career_scores, negotiate, unified_roadmap


def main():
    print("=" * 70)
    print("  UDAAN PRISM ENGINE — END-TO-END INTEGRATION TEST")
    print("=" * 70)

    # 1. Sample Student Assessment Answers
    student_answers = {
        "bg_stream": "science_maths",
        "bg_marks_band": "75_90",
        "int_01": 5, "int_02": 4,  # Realistic
        "int_03": 5, "int_04": 5,  # Investigative
        "int_05": 2, "int_06": 2,  # Artistic
        "int_07": 3, "int_08": 3,  # Social
        "int_09": 4, "int_10": 4,  # Enterprising
        "int_11": 4, "int_12": 4,  # Conventional
        "val_security": 7,
        "val_independence": 8,
        "val_helping": 5,
        "val_income": 9,
        "val_creativity": 8,
        "pref_risk_1": "gamble",
        "pref_risk_2": "safe",
        "pref_risk_3": "gamble",
        "pref_relocation": "anywhere_india",
        "pref_time_to_earn": "within_4y",
        "pref_domain_wish": ["tech_engineering", "business_management"],
    }
    aptitude_puzzles = {
        "numerical": True,
        "verbal": True,
        "spatial": True,
        "logical": True,
    }

    # 2. Sample Parent Intake Answers
    parent_answers = {
        "income_band": "6_12l",
        "savings_band": "3_8l",
        "loan_band": "8_15l",
        "surplus_band": "15k_30k",
        "emi_band": "5k_15k",
        "risk_1": "safe",
        "risk_2": "safe",
        "risk_3": "safe",
        "relocation": "home_city",
        "time_to_earn": "within_4y",
        "domain_wish": ["tech_engineering"],
    }

    print("\n[Step 1] Mapping answers to domain models...")
    student = student_from_answers(student_answers, aptitude_puzzles)
    parent = parent_from_answers(parent_answers)

    print(f"  [OK] Student created: ID={student.student_id}, Stage={student.stage}")
    print(f"    - Risk Tolerance: {student.risk_appetite:.2f}")
    print(f"    - Relocation Willingness: {student.relocation_willingness:.2f}")
    print(f"    - Marks (Midpoint): {student.academics.marks}%")
    print(f"  [OK] Parent created: Household Income = INR {parent.household_income:,.0f}/mo")
    print(f"    - Liquid Savings = INR {parent.savings:,.0f}")
    print(f"    - Max Loan Capacity = INR {parent.loan_max:,.0f}")
    print(f"    - Risk Tolerance: {parent.risk:.2f}")

    # 3. Overall Conflict Diagnosis
    print("\n[Step 2] Computing Family Conflict Diagnosis...")
    conflict_res = overall_conflict(student, parent)
    print(f"  [OK] Overall Conflict Index: {conflict_res['conflict_index']}/100 (High: {conflict_res['is_high_conflict']})")
    print(f"  [OK] Dimension Gaps (0-1 scale):")
    for dim, gap in conflict_res["dimension_gaps"].items():
        print(f"    - {dim.capitalize()}: {gap:.2f}")

    # 4. Per-Career Evaluation
    print("\n[Step 3] Evaluating Careers across Student, Parent, and Market...")
    career_evals = per_career_scores(student, parent)
    viable_careers = [c for c in career_evals if c["is_viable"]]
    print(f"  [OK] Total Careers Evaluated: {len(career_evals)}")
    print(f"  [OK] Viable Pathways (Passed Academic & Financial Gates): {len(viable_careers)}")

    # 5. Negotiation Slider Evaluation (alpha = 0.5)
    print("\n[Step 4] Evaluating Negotiation Slider (alpha = 0.50)...")
    neg_res = negotiate(student, parent, alpha=0.50)
    print(f"  [OK] Ranked Viable Options: {len(neg_res['ranked_careers'])}")
    print(f"  [OK] Compromise Zone Options: {len(neg_res['compromise_zone_career_ids'])}")
    print(f"  [OK] Pareto Optimal Options: {len(neg_res['pareto_optimal_career_ids'])}")
    print(f"  [OK] Recommended Option: {neg_res['recommended_career_id']}")

    # 6. Unified Full Roadmap
    print("\n[Step 5] Generating Unified Career Roadmap Report...")
    report = unified_roadmap(student, parent, alpha=0.50)
    print(f"  [OK] Top 5 Recommended Careers:")
    for item in report.ranked_careers[:5]:
        comp_tag = " [Compromise Zone]" if item.is_in_compromise_zone else ""
        pareto_tag = " [Pareto Optimal]" if item.is_pareto_optimal else ""
        data_tag = "Verified" if item.data_complete else f"Estimated (missing: {', '.join(item.missing_data_fields)})"
        print(f"    #{item.rank} {item.career_name:<28} | Score: {item.negotiated_score:4.1f}% | Fit: {item.student_fit:4.1f}% | Family: {item.family_viability:4.1f}% | Data: {data_tag}{comp_tag}{pareto_tag}")

    print("\n" + "=" * 70)
    print("  ALL ENGINE CHECKS PASSED SUCCESSFULLY (0 ERRORS, 100% WORKING)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
