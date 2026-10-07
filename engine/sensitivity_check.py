"""Sensitivity Analysis for PRISM Engine Financial Thresholds (Fix 7).

Evaluates the impact of shifting financial solver thresholds by +/-10% (one at a time)
on the Compromise Zone across representative demo families.

Thresholds evaluated:
1. rb_gate_max (Repayment Burden Gate Max)
2. dsr_gate_max (Debt Service Ratio Gate Max)
3. rb_comfort_threshold (Repayment Burden Comfort Level)
4. dsr_comfort_threshold (Debt Service Ratio Comfort Level)
5. payback_horizon_years (Payback Horizon)
6. payback_income_share (Payback Income Share)

Design assumption comments:
"design assumption, unsourced, verify against bank lending norms"
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.parent.config import DEFAULT_CONFIG as BASELINE_PARENT_CONFIG, ParentSolverConfig
from engine.parent.models import ParentProfile, SectorRatings
from engine.student_fit.models import Student
from engine.public import get_default_student_careers, get_default_routes
from engine.synthesis import generate_unified_roadmap
from engine.answer_mapping import student_from_answers, parent_from_answers


def get_demo_families() -> List[Tuple[str, Student, ParentProfile]]:
    """Return representative demo student + family pairs for sensitivity testing."""
    # 1. Standard Middle-Income Demo Family (from demo_run.py)
    student_answers = {
        "bg_stream": "science_maths",
        "bg_marks_band": "75_90",
        "int_01": 5, "int_02": 4,  # Realistic
        "int_03": 5, "int_04": 5,  # Investigative
        "int_05": 2, "int_06": 2,  # Artistic
        "int_07": 3, "int_08": 3,  # Social
        "int_09": 4, "int_10": 4,  # Enterprising
        "int_11": 4, "int_12": 4,  # Conventional
        "val_security": 7, "val_independence": 8, "val_helping": 5,
        "val_income": 9, "val_creativity": 8,
        "pref_risk_1": "gamble", "pref_risk_2": "safe", "pref_risk_3": "gamble",
        "pref_relocation": "anywhere_india",
        "pref_time_to_earn": "within_4y",
        "pref_domain_wish": ["tech_engineering", "business_management"],
    }
    aptitudes = {"numerical": True, "verbal": True, "spatial": True, "logical": True}
    student_1 = student_from_answers(student_answers, aptitudes)

    parent_answers_1 = {
        "income_band": "6_12l",
        "savings_band": "3_8l",
        "loan_band": "8_15l",
        "surplus_band": "15k_30k",
        "emi_band": "5k_15k",
        "risk_1": "safe", "risk_2": "safe", "risk_3": "safe",
        "relocation": "home_city",
        "time_to_earn": "within_4y",
        "domain_wish": ["tech_engineering"],
    }
    parent_1 = parent_from_answers(parent_answers_1)

    # 2. Financially Constrained / Low-Income Family
    parent_2 = ParentProfile(
        savings=150000.0,
        monthly_surplus=3500.0,
        household_income=28000.0,
        existing_emis=2000.0,
        loan_max=250000.0,
        domain_ratings={"tech_engineering": 5, "business_management": 3},
        sector_ratings=SectorRatings(govt=5, private=3, entrepreneurship=2),
        min_salary=400000.0,
        max_years_to_income=4.0,
        relocation_willingness=0.50,
        risk=0.30,
    )

    # 3. Aspirant Upper-Middle Family
    parent_3 = ParentProfile(
        savings=750000.0,
        monthly_surplus=25000.0,
        household_income=120000.0,
        existing_emis=10000.0,
        loan_max=1200000.0,
        domain_ratings={"tech_engineering": 5, "business_management": 4},
        sector_ratings=SectorRatings(govt=3, private=5, entrepreneurship=4),
        min_salary=700000.0,
        max_years_to_income=5.0,
        relocation_willingness=0.80,
        risk=0.60,
    )

    return [
        ("Demo Middle-Class Family (Default Intake)", student_1, parent_1),
        ("Constrained Budget Family (Tight Liquidity)", student_1, parent_2),
        ("Upper-Middle Aspirant Family (Higher Capacity)", student_1, parent_3),
    ]


THRESHOLDS_TO_TEST = [
    ("rb_gate_max", "RB Max Gate (Hard Gate)"),
    ("dsr_gate_max", "DSR Max Gate (Hard Gate)"),
    ("rb_comfort_threshold", "RB Comfort Level (Soft Score)"),
    ("dsr_comfort_threshold", "DSR Comfort Level (Soft Score)"),
    ("payback_horizon_years", "Payback Horizon (Years)"),
    ("payback_income_share", "Payback Income Share"),
]


def run_single_family_sensitivity(
    family_label: str,
    student: Student,
    parent: ParentProfile,
    careers: List[Any],
    routes: List[Any],
) -> List[Dict[str, Any]]:
    """Run sensitivity checks for all 6 thresholds on a single family."""
    # 1. Baseline Compromise Zone
    baseline_rep = generate_unified_roadmap(
        student=student,
        parent=parent,
        student_careers=careers,
        routes=routes,
        parent_config=BASELINE_PARENT_CONFIG,
    )
    baseline_compromise: Set[str] = {
        item.career_id for item in baseline_rep.compromise_zone_careers
    }

    results: List[Dict[str, Any]] = []

    for attr_name, display_name in THRESHOLDS_TO_TEST:
        baseline_val = getattr(BASELINE_PARENT_CONFIG, attr_name)

        # Shift -10%
        val_minus = baseline_val * 0.90
        cfg_minus = BASELINE_PARENT_CONFIG.with_overrides(**{attr_name: val_minus})
        rep_minus = generate_unified_roadmap(
            student=student,
            parent=parent,
            student_careers=careers,
            routes=routes,
            parent_config=cfg_minus,
        )
        minus_compromise: Set[str] = {
            item.career_id for item in rep_minus.compromise_zone_careers
        }
        entered_minus = sorted(list(minus_compromise - baseline_compromise))
        left_minus = sorted(list(baseline_compromise - minus_compromise))

        # Shift +10%
        val_plus = baseline_val * 1.10
        cfg_plus = BASELINE_PARENT_CONFIG.with_overrides(**{attr_name: val_plus})
        rep_plus = generate_unified_roadmap(
            student=student,
            parent=parent,
            student_careers=careers,
            routes=routes,
            parent_config=cfg_plus,
        )
        plus_compromise: Set[str] = {
            item.career_id for item in rep_plus.compromise_zone_careers
        }
        entered_plus = sorted(list(plus_compromise - baseline_compromise))
        left_plus = sorted(list(baseline_compromise - plus_compromise))

        results.append({
            "param": attr_name,
            "label": display_name,
            "baseline": baseline_val,
            "baseline_count": len(baseline_compromise),
            "minus_10_val": round(val_minus, 4),
            "minus_count": len(minus_compromise),
            "entered_minus": entered_minus,
            "left_minus": left_minus,
            "plus_10_val": round(val_plus, 4),
            "plus_count": len(plus_compromise),
            "entered_plus": entered_plus,
            "left_plus": left_plus,
        })

    return results


def run_all_sensitivity_checks() -> None:
    """Run sensitivity checks across all demo families and print formatted report tables."""
    print("=" * 115)
    print("      PRISM ENGINE — FINANCIAL THRESHOLD SENSITIVITY CHECK (FIX 7)")
    print("      Perturbation: -10% and +10% per threshold (One-at-a-time, OAT)")
    print("      Note: All thresholds are design assumptions (unsourced, verify against bank lending norms)")
    print("=" * 115)

    careers = get_default_student_careers()
    routes = get_default_routes()
    families = get_demo_families()

    for fam_name, student, parent in families:
        print(f"\nFamily Profile: {fam_name}")
        print(f"Income: INR {parent.household_income:,.0f}/mo | Savings: INR {parent.savings:,.0f} | Loan Max: INR {parent.loan_max:,.0f}")
        print("-" * 115)

        table_data = run_single_family_sensitivity(fam_name, student, parent, careers, routes)

        header = (
            f"{'Threshold Parameter':<32} | {'Base':<6} | "
            f"{'-10% Shift':<11} | {'Enter':<5} | {'Leave':<5} | "
            f"{'+10% Shift':<11} | {'Enter':<5} | {'Leave':<5} | {'Stability'}"
        )
        print(header)
        print("-" * 115)

        for row in table_data:
            net_change_minus = len(row["entered_minus"]) + len(row["left_minus"])
            net_change_plus = len(row["entered_plus"]) + len(row["left_plus"])
            is_stable = (net_change_minus == 0 and net_change_plus == 0)
            stability_str = "STABLE (0)" if is_stable else f"SHIFT ({net_change_minus}/{net_change_plus})"

            r_str = (
                f"{row['label']:<32} | "
                f"{row['baseline']:<6.3f} | "
                f"{row['minus_10_val']:<11.3f} | "
                f"{len(row['entered_minus']):<5} | "
                f"{len(row['left_minus']):<5} | "
                f"{row['plus_10_val']:<11.3f} | "
                f"{len(row['entered_plus']):<5} | "
                f"{len(row['left_plus']):<5} | "
                f"{stability_str}"
            )
            print(r_str)

            # Print career transitions if any
            if row["entered_minus"]:
                print(f"    [-10%] Careers entering: {', '.join(row['entered_minus'])}")
            if row["left_minus"]:
                print(f"    [-10%] Careers leaving:  {', '.join(row['left_minus'])}")
            if row["entered_plus"]:
                print(f"    [+10%] Careers entering: {', '.join(row['entered_plus'])}")
            if row["left_plus"]:
                print(f"    [+10%] Careers leaving:  {', '.join(row['left_plus'])}")

        print("-" * 115)

    print("\n[OK] Sensitivity analysis completed successfully. No threshold values modified in config.")
    print("=" * 115 + "\n")


if __name__ == "__main__":
    run_all_sensitivity_checks()
