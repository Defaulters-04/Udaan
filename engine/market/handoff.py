"""Provisional multi-machine hand-off combining Student, Family, and Market scores."""

from typing import List, Tuple, Optional
from .config import MarketSolverConfig, DEFAULT_CONFIG
from .models import CareerScoreInput, RankedCareer, BlockedCareer, HandoffResult


def conflict_per_career(f_student: float, f_family: float) -> float:
    """conflict_per_career(F_student, F_family) = abs(F_student - F_family)."""
    return abs(float(f_student) - float(f_family))


def calculate_composite_score(
    f_student: float,
    f_family: float,
    f_market: float,
    config: MarketSolverConfig = DEFAULT_CONFIG,
) -> float:
    """composite(F_student, F_family, F_market) = 0.45*F_student + 0.35*F_family + 0.20*F_market."""
    return (
        config.w_handoff_student * float(f_student)
        + config.w_handoff_family * float(f_family)
        + config.w_handoff_market * float(f_market)
    )


def calculate_final_score(
    f_composite: float,
    conflict_c: float,
    config: MarketSolverConfig = DEFAULT_CONFIG,
) -> float:
    """final(F_composite, C_c, penalty=0.10) = F_composite * (1 - penalty * C_c / 100)."""
    penalty_factor = 1.0 - (config.conflict_penalty * (float(conflict_c) / 100.0))
    return float(f_composite) * penalty_factor


def rank_careers(
    inputs: List[CareerScoreInput],
    config: MarketSolverConfig = DEFAULT_CONFIG,
) -> HandoffResult:
    """Rank careers across student, family, and market dimensions, filtering blocked pathways."""
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

        conflict = conflict_per_career(item.F_student, item.F_family)
        comp = calculate_composite_score(item.F_student, item.F_family, item.F_market, config)
        fin = calculate_final_score(comp, conflict, config)

        candidates.append({
            "career_id": item.career_id,
            "F_student": item.F_student,
            "F_family": item.F_family,
            "F_market": item.F_market,
            "conflict_score": round(conflict, 2),
            "composite_score": round(comp, 2),
            "final_score": round(fin, 2),
        })

    # Sort descending by final_score
    candidates.sort(key=lambda x: x["final_score"], reverse=True)

    for rank_idx, c in enumerate(candidates, 1):
        ranked.append(
            RankedCareer(
                rank=rank_idx,
                career_id=c["career_id"],
                F_student=c["F_student"],
                F_family=c["F_family"],
                F_market=c["F_market"],
                conflict_score=c["conflict_score"],
                composite_score=c["composite_score"],
                final_score=c["final_score"],
            )
        )

    return HandoffResult(ranked=ranked, blocked=blocked)
