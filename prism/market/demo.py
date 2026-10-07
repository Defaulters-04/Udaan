"""Demonstration script for PRISM Engine - Market Machine Module.

Loads illustrative demo snapshot careers and evaluates family-independent
market viability scores, honest uncertainty ranges, and confidence audits.
"""

import sys
from pathlib import Path

# Ensure repository root is in sys.path when executed directly as a script
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from prism.market.config import DEFAULT_CONFIG
from prism.market.data_loader import (
    load_careers_snapshot,
    load_regional_totals_snapshot,
    DEFAULT_DEMO_CAREERS_FILE,
)
from prism.market.scores import evaluate_market_catalogue


def run_demo() -> None:
    """Run illustrative market evaluation demo and format results as a clean table."""
    print("=" * 125)
    print("       PRISM ENGINE (UDAAN) - MARKET MACHINE CAREER VIABILITY & UNCERTAINTY DEMO")
    print("=" * 125)
    print("NOTE: All figures and career trajectories are ILLUSTRATIVE placeholder data for offline testing.\n")

    careers = load_careers_snapshot(DEFAULT_DEMO_CAREERS_FILE)
    try:
        totals = load_regional_totals_snapshot()
    except Exception:
        totals = None

    student_region = "bengaluru"
    print(f"[INPUT CONFIGURATION]")
    print(f"  * Catalogue size:           {len(careers)} illustrative careers")
    print(f"  * Target Student Region:    '{student_region}'")
    print(f"  * Forecasting Ladder:       ETS (>=24pts) -> OLS (12-23pts) -> Curated Fallback (<12pts)")
    print(f"  * Default Component Weights: Demand(0.25), Trend(0.30), PayYield(0.20), Disruption(0.15), Local(0.10)\n")

    result = evaluate_market_catalogue(
        careers=careers,
        regional_totals=totals,
        student_region=student_region,
        config=DEFAULT_CONFIG,
    )

    # Print Formatted Table
    print("--- 1. CAREER MARKET VIABILITY EVALUATION (RANKED BY PESSIMISTIC F_MARKET) ---")
    header = (
        f"{'Career ID':<30} | {'F_mkt (Low)':<11} | {'Central':<8} | {'Optimistic':<10} | "
        f"{'Method':<16} | {'Confidence':<10} | {'Risk Proxy':<10}"
    )
    print("-" * len(header))
    print(header)
    print("-" * len(header))

    for r in result.sorted_careers:
        row = (
            f"{r.career_id:<30} | "
            f"{r.F_market:>9.1f}/100 | "
            f"{r.F_market_central:>6.1f}/100 | "
            f"{r.F_market_optimistic:>8.1f}/100 | "
            f"{r.trend_method[:16]:<16} | "
            f"{r.overall_confidence.upper():<10} | "
            f"{r.risk_proxy:>8.2f}"
        )
        print(row)
    print("-" * len(header))

    # Print Low-Confidence / Flagged Careers Audit
    print("\n--- 2. DATA CONFIDENCE & AUDIT FLAGS ---")
    if result.low_confidence_careers:
        print(f"Identified {len(result.low_confidence_careers)} low-confidence career(s) (always retained, never hidden):")
        for lc in result.low_confidence_careers:
            print(f"  * [{lc.career_id}]: Overall Confidence = {lc.overall_confidence.upper()} ({lc.confidence_score:.0%})")
            for flag in lc.flags:
                print(f"      - Flag: {flag}")
    else:
        print("All careers met high or medium data confidence standards.")

    print("\n--- 3. SAMPLE EXPLANATIONS (RULE-BASED FACTUAL SUMMARY) ---")
    for r in result.sorted_careers[:3]:
        print(f"  * [{r.career_id}]: {r.explanation}")

    print("\n" + "=" * 125)


if __name__ == "__main__":
    run_demo()
