"""Provisional multi-machine hand-off combining Student, Family, and Market scores."""

from typing import List, Tuple, Optional
from .config import MarketSolverConfig, DEFAULT_CONFIG
from .models import CareerScoreInput, RankedCareer, BlockedCareer, HandoffResult


def fit_gap_per_career(f_student: float, f_family: float) -> float:
    """fit_gap_per_career(F_student, F_family) = abs(F_student - F_family) (Fix 2)."""
    return abs(float(f_student) - float(f_family))


# Alias for backward compatibility
conflict_per_career = fit_gap_per_career


def calculate_composite_score(
    f_student: float,
    f_family: float,
    f_market: float = 0.0,
    config: MarketSolverConfig = DEFAULT_CONFIG,
) -> float:
    """Composite ranking score."""
    w_s = config.w_handoff_student
    w_f = config.w_handoff_family
    w_m = config.w_handoff_market
    total = w_s + w_f + w_m
    if total <= 0.0:
        total = 1.0
    return (w_s * float(f_student) + w_f * float(f_family) + w_m * float(f_market)) / total


def calculate_final_score(
    f_composite: float,
    conflict_c: float = 0.0,
    config: MarketSolverConfig = DEFAULT_CONFIG,
) -> float:
    """Fix 1: Deleted the composite multiplier (1 - penalty * conflict/100). Final score equals composite score."""
    return float(f_composite)


def rank_careers(
    inputs: List[CareerScoreInput],
    config: MarketSolverConfig = DEFAULT_CONFIG,
) -> HandoffResult:
    """Rank careers across student and family dimensions with fit_gap (Fix 1, Fix 2)."""
    ranked: List[RankedCareer] = []
    blocked: List[BlockedCareer] = []

    candidates = []

    for item in inputs:
        reasons = []
        if item.G_fin == 0:
            reasons.append("Financial feasibility gate failed (G_fin=0)")
        if item.G_acad == 0:
            reasons.append("Academic gate failed (G_acad=0)")

        if reasons:
            blocked.append(BlockedCareer(career_id=item.career_id, reasons=reasons))
            continue

        gap = fit_gap_per_career(item.F_student, item.F_family)
        comp = calculate_composite_score(item.F_student, item.F_family, item.F_market, config)
        fin = calculate_final_score(comp, gap, config)

        candidates.append({
            "career_id": item.career_id,
            "F_student": item.F_student,
            "F_family": item.F_family,
            "F_market": item.F_market,
            "fit_gap": round(gap, 2),
            "composite_score": round(comp, 2),
            "final_score": round(fin, 2),
        })

    # Sort descending by final_score, then tie-break by F_market
    candidates.sort(key=lambda x: (x["final_score"], x["F_market"]), reverse=True)

    for rank_idx, c in enumerate(candidates, 1):
        ranked.append(
            RankedCareer(
                rank=rank_idx,
                career_id=c["career_id"],
                F_student=c["F_student"],
                F_family=c["F_family"],
                F_market=c["F_market"],
                fit_gap=c["fit_gap"],
                composite_score=c["composite_score"],
                final_score=c["final_score"],
            )
        )

    return HandoffResult(ranked=ranked, blocked=blocked)
