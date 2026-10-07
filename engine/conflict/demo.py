"""Demonstration script for PRISM Engine - Conflict Index & Negotiation Explorer Module.

Demonstrates:
1. Family Diagnosis on shared dimensions (risk appetite, domain preferences, relocation, time-to-income).
2. Per-career conflict reports across diverse educational/career pathways.
3. Negotiation Explorer slider (alpha = 0.5 compromise zone).
4. Composite score blending with conflict penalties.
"""

import sys
from pathlib import Path
from typing import List

# Ensure repository root is in sys.path when executed directly as a script
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.conflict.config import DEFAULT_CONFIG
from engine.conflict.models import (
    StudentConflictInput,
    ParentConflictInput,
    RouteConflictInput,
    ScoredCareerInput,
)
from engine.conflict.scores import (
    compute_overall_conflict,
    compute_career_conflict,
    evaluate_conflict,
    evaluate_negotiation_slider,
    compute_composite_score,
)


def run_demo() -> None:
    """Run illustrative conflict index and negotiation demo."""
    print("=" * 105)
    print("       PRISM ENGINE (UDAAN) - CONFLICT INDEX & NEGOTIATION EXPLORER DEMO")
    print("=" * 105)
    print("NOTE: All figures are ILLUSTRATIVE placeholder data for demonstration purposes.\n")

    # 1. Student and Parent Profiles
    student = StudentConflictInput(
        student_id="student_arjun",
        risk_appetite=0.85,  # High risk tolerance (eager for startups / cutting-edge tech)
        domain_preference={
            "Technology & Engineering": 5.0,
            "Design & Creative Arts": 4.0,
            "Business & Management": 3.0,
            "Government & Public Sector": 1.0,
        },
        relocation_willingness=0.90,  # Willing to move anywhere (Tier-1 hub / abroad)
        max_years_to_income=5.0,     # Envisions 4-5 years of rigorous study & specialization
    )

    parent = ParentConflictInput(
        risk=0.25,  # Risk-averse, prioritizes stability and timely return on investment
        domain_ratings={
            "Technology & Engineering": 4.0,
            "Design & Creative Arts": 2.0,
            "Business & Management": 3.0,
            "Government & Public Sector": 5.0,
        },
        relocation_willingness=0.30,  # Strongly prefers staying near home state / region
        max_years_to_income=3.0,     # Family cashflow requires income within 3 years
    )

    print("--- 1. MULTI-STAKEHOLDER PROFILES (SHARED DIMENSIONS) ---")
    print(f"  Dimension                   Student (Arjun)        Parent (Father)        Gap")
    print("  " + "-" * 75)

    report = compute_overall_conflict(student, parent)
    print(f"  * Risk Appetite:            {student.risk_appetite:.2f} (Seeking)          {parent.risk:.2f} (Cautious)         {report.risk_conflict.gap:.1%}")
    print(f"  * Relocation Willingness:   {student.relocation_willingness:.2f} (Global/Metro)     {parent.relocation_willingness:.2f} (Local/Regional)    {report.relocation_conflict.gap:.1%}")
    print(f"  * Time to First Income:     {student.max_years_to_income:.1f} years              {parent.max_years_to_income:.1f} years              {report.time_conflict.gap:.1%}")
    print(f"  * Domain Misalignment:      Tech (5) / Arts (4)    Govt (5) / Tech (4)    {report.domain_conflict.gap:.1%}")

    print("\n--- 2. OVERALL FAMILY CONFLICT DIAGNOSIS (FAMILY MIRROR) ---")
    print(f"  * Overall Conflict Score:   {report.overall_conflict:.2f} / 1.00 ({report.overall_conflict*100:.1f}%)")
    print(f"  * High Conflict Flag:       {'YES (Requires Mediation)' if report.is_high_conflict else 'NO (Normal Alignment)'}")
    print(f"  * Diagnostic Narrative:     {report.diagnosis_summary}")
    print("\n  * Dimension Breakdown:")
    for dim, exp in report.dimension_explanations.items():
        print(f"    - [{dim.upper()}]: {exp}")

    # 3. Candidate Career Routes
    candidate_careers: List[ScoredCareerInput] = [
        ScoredCareerInput(
            career_id="ai_startup_founder",
            route_id="incubator_route",
            career_name="AI Startup Founder",
            student_fit=0.94,
            family_viability=0.25,
            market_score=0.82,
            career_risk=0.90,
            domain="Technology & Engineering",
            relocation_need=0.95,
            years_to_first_income=5.0,
            is_financially_viable=False,
        ),
        ScoredCareerInput(
            career_id="cloud_devops_engineer",
            route_id="state_btech_route",
            career_name="Cloud & DevOps Engineer (State Govt College)",
            student_fit=0.86,
            family_viability=0.88,
            market_score=0.89,
            career_risk=0.40,
            domain="Technology & Engineering",
            relocation_need=0.45,
            years_to_first_income=4.0,
            is_financially_viable=True,
        ),
        ScoredCareerInput(
            career_id="public_sector_bank_it",
            route_id="ibps_exam_route",
            career_name="Public Sector Bank IT Officer",
            student_fit=0.45,
            family_viability=0.92,
            market_score=0.74,
            career_risk=0.15,
            domain="Government & Public Sector",
            relocation_need=0.30,
            years_to_first_income=3.0,
            is_financially_viable=True,
        ),
        ScoredCareerInput(
            career_id="ui_ux_designer",
            route_id="pvt_design_school",
            career_name="UI/UX Designer (Private Design Academy)",
            student_fit=0.80,
            family_viability=0.52,
            market_score=0.76,
            career_risk=0.60,
            domain="Design & Creative Arts",
            relocation_need=0.70,
            years_to_first_income=4.0,
            is_financially_viable=True,
        ),
    ]

    print("\n--- 3. NEGOTIATION EXPLORER (ALPHA = 0.50: BALANCED COMPROMISE) ---")
    neg_res = evaluate_negotiation_slider(student, parent, candidate_careers, alpha=0.50)

    print(f"  Total Options Evaluated: {neg_res.total_careers_evaluated} | Options in Compromise Zone: {neg_res.compromise_zone_count}\n")
    print(
        f"{'Career Name':<42} | {'Student':<7} | {'Family':<7} | {'Conflict':<8} | {'Score':<6} | {'In Compromise?':<14} | {'Pareto?'}"
    )
    print("-" * 105)
    for c in neg_res.ranked_careers:
        in_comp = "YES" if c.is_in_compromise_zone else "NO"
        pareto = "YES" if c.is_pareto_optimal else "NO"
        print(
            f"{c.career_name:<42} | {c.student_fit*100:>5.1f}% | {c.family_viability*100:>5.1f}% | {c.career_conflict*100:>6.1f}% | {c.negotiated_score*100:>5.1f} | {in_comp:<14} | {pareto}"
        )

    print("\n--- 4. COMPROMISE ZONE HIGHLIGHT ---")
    if neg_res.compromise_zone_careers:
        top_comp = neg_res.compromise_zone_careers[0]
        print(f"  * Recommended Compromise Career: '{top_comp.career_name}'")
        print(f"    - Student Fit: {top_comp.student_fit*100:.1f}%")
        print(f"    - Family Affordability / Viability: {top_comp.family_viability*100:.1f}%")
        print(f"    - Conflict Gap: {top_comp.career_conflict*100:.1f}%")
        print(f"    - Why it works: {top_comp.summary_reason}")
    else:
        print("  No careers currently qualify in the Compromise Zone.")

    print("\n--- 5. COMPOSITE BLENDING FORMULA VERIFICATION ---")
    comp_score = compute_composite_score(
        student_fit=0.86,
        family_viability=0.88,
        market_score=0.89,
        career_conflict=0.15,
        config=DEFAULT_CONFIG,
    )
    print(f"  * Blended Composite Score for Cloud & DevOps Engineer: {comp_score*100:.1f} / 100")
    print("=" * 105)


if __name__ == "__main__":
    run_demo()
