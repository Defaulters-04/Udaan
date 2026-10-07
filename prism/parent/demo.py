"""Demonstration script for PRISM Engine - Parent Machine Module.

Loads one illustrative demo family profile and 3 illustrative educational pathways,
evaluating financial constraints, family scores, and actionable blocked remedies.
"""

import sys
from pathlib import Path
from typing import List

# Ensure repository root is in sys.path when executed directly as a script
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from prism.parent.config import DEFAULT_CONFIG
from prism.parent.models import ParentProfile, Route, SectorRatings
from prism.parent.scores import evaluate_parent_portfolio


def run_demo() -> None:
    """Run illustrative parent evaluation demo and format results as a clean table."""
    print("=" * 105)
    print("       PRISM ENGINE (UDAAN) - PARENT MACHINE CONSTRAINTS & FAMILY SCORING DEMO")
    print("=" * 105)
    print("NOTE: All figures are ILLUSTRATIVE placeholder data for demonstration purposes.\n")

    # 1. Illustrative Demo Family Profile
    demo_profile = ParentProfile(
        savings=350000.0,            # INR 3.5 Lakhs
        monthly_surplus=6000.0,      # INR 6,000 / month
        household_income=45000.0,    # INR 45,000 / month
        existing_emis=2500.0,        # INR 2,500 / month
        loan_max=400000.0,           # INR 4.0 Lakhs max education loan
        domain_ratings={
            "technology": 5,
            "business": 3,
            "arts": 2,
        },
        sector_ratings=SectorRatings(govt=4, private=5, entrepreneurship=3),
        min_salary=600000.0,         # INR 6.0 Lakhs / year
        max_years_to_income=5.0,     # Max 5 years to income
        relocation_willingness=0.75, # 75% willingness
        risk=0.45,                   # Moderate-conservative risk tolerance
    )

    print("--- 1. DEMO FAMILY PROFILE (ILLUSTRATIVE) ---")
    print(f"  * Liquid Savings (S):           INR {demo_profile.savings:,.0f}")
    print(f"  * Monthly Disposable Surplus (M): INR {demo_profile.monthly_surplus:,.0f}")
    print(f"  * Monthly Household Income:     INR {demo_profile.household_income:,.0f}")
    print(f"  * Existing EMIs:                INR {demo_profile.existing_emis:,.0f}")
    print(f"  * Max Loan Capacity (L_max):     INR {demo_profile.loan_max:,.0f}")
    print(f"  * Min Acceptable Salary:        INR {demo_profile.min_salary:,.0f}/year")
    print(f"  * Parental Risk Tolerance (R_p): {demo_profile.risk:.2f}")
    print(f"  * Relocation Willingness:       {demo_profile.relocation_willingness:.2f}\n")

    # 2. Three Illustrative Candidate Routes for "software_developer"
    demo_routes: List[Route] = [
        # Route 1: Affordable State University Pathway
        Route(
            career_id="software_developer",
            route_id="route_state_univ",
            tuition=240000.0,
            living=120000.0,
            exam_equipment=15000.0,
            grant=25000.0,
            duration_years=4.0,
            starting_salary=650000.0,
            years_to_first_income=4.0,
            career_risk=0.30,
            relocation_need=0.20,
            domain="technology",
            sector="private",
            g_acad=1,
        ),
        # Route 2: Tier-1 Premier Institute Pathway (High ROI, Moderate Cost)
        Route(
            career_id="software_developer",
            route_id="route_premier_inst",
            tuition=500000.0,
            living=200000.0,
            exam_equipment=20000.0,
            grant=50000.0,
            duration_years=4.0,
            starting_salary=1100000.0,
            years_to_first_income=4.0,
            career_risk=0.25,
            relocation_need=0.60,
            domain="technology",
            sector="private",
            g_acad=1,
        ),
        # Route 3: High-Cost Private College Pathway (Exceeds Loan Limits -> Blocked)
        Route(
            career_id="software_developer",
            route_id="route_private_elite",
            tuition=1200000.0,
            living=400000.0,
            exam_equipment=50000.0,
            grant=0.0,
            duration_years=4.0,
            starting_salary=750000.0,
            years_to_first_income=4.0,
            career_risk=0.35,
            relocation_need=0.85,
            domain="technology",
            sector="private",
            g_acad=1,
        ),
    ]

    response = evaluate_parent_portfolio(demo_profile, demo_routes, DEFAULT_CONFIG)

    # 3. Print Evaluation Table
    print("--- 2. ROUTE VIABILITY & FAMILY FIT EVALUATION ---")
    header = (
        f"{'Route ID':<20} | {'Net Cost':<10} | {'Cash Cap':<10} | {'Loan Req':<10} | "
        f"{'EMI':<8} | {'RB':<6} | {'DSR':<6} | {'Payback':<7} | {'Gate':<5} | "
        f"{'F_fin':<6} | {'F_asp':<6} | {'F_risk':<6} | {'F_fam':<6}"
    )
    print("-" * len(header))
    print(header)
    print("-" * len(header))

    for r in response.reports:
        gate_str = "PASS" if r.gate_cleared == 1 else "BLOCK"
        row = (
            f"{r.route_id:<20} | "
            f"INR {r.cost_net:>8,.0f} | "
            f"INR {r.cash_available:>8,.0f} | "
            f"INR {r.loan_needed:>8,.0f} | "
            f"INR {r.emi:>6,.0f} | "
            f"{r.repayment_burden:>5.1%} | "
            f"{r.debt_service_ratio:>5.1%} | "
            f"{r.payback_years:>5.1f}y | "
            f"{gate_str:<5} | "
            f"{r.f_financial:>6.1f} | "
            f"{r.f_aspiration:>6.1f} | "
            f"{r.f_risk:>6.1f} | "
            f"{r.f_family:>6.1f}"
        )
        print(row)
    print("-" * len(header))

    # 4. Career Aggregation
    print("\n--- 3. CAREER RECOMMENDATION ---")
    for cid, ceval in response.career_results.items():
        best = ceval.best_route
        best_name = best.route_id if best else "None"
        print(f"Target Career: {cid}")
        print(f"  * Recommended Best Route: {best_name} (F_family = {ceval.f_family_career:.1f}/100)")
        print("  * Alternative Routes (Ranked by Family Score):")
        for idx, alt in enumerate(ceval.alternatives, 1):
            status = "Viable" if alt.gate_cleared == 1 else "Blocked"
            print(f"     {idx}. {alt.route_id:<20} -> F_family: {alt.f_family:>5.1f} | Status: {status}")

    # 5. Actionable Blocked List
    print("\n--- 4. ACTIONABLE BLOCKED ROUTES & SHORTFALL REMEDIATION ---")
    if response.blocked_list:
        for b in response.blocked_list:
            print(f"\n[BLOCKED] Route: '{b.route_id}' in career '{b.career_id}'")
            print(f"  - Net Pathway Cost:       INR {b.cost_net:,.0f}")
            print(f"  - Loan Funding Gap:       INR {b.funding_gap:,.0f}")
            print(f"  - Failures Identified:    {', '.join(b.block_reasons)}")
            print(f"  - Calculated Shortfall:   INR {b.shortfall_grant_needed:,.0f}")
            print(f"  - Actionable Suggestion:  {b.suggestion}")
    else:
        print("All routes cleared financial and academic gates!")

    print("\n" + "=" * 105)


if __name__ == "__main__":
    run_demo()
