"""Component calculation and catalogue-wide ranking for PRISM Market Machine."""

from typing import List, Dict, Optional, Tuple, Any
import numpy as np
import pandas as pd
from scipy.stats import rankdata

from .config import MarketSolverConfig, DEFAULT_CONFIG
from .models import CareerMarketRecord, RegionalTotals, ComponentDetail


def clamp(val: float, low: float = 0.0, high: float = 1.0) -> float:
    """clamp(x) = max(low, min(high, x))."""
    return max(low, min(high, float(val)))


def calculate_percentile_ranks(
    values: List[Optional[float]],
    config: MarketSolverConfig = DEFAULT_CONFIG,
) -> Tuple[List[Optional[float]], List[str]]:
    """Compute percentile ranks across catalogue: (rank - 1) / (N - 1) with ties averaged.

    If N < 5, uses min-max scaling.
    If N = 1, returns 0.5 with diagnostic flag.
    """
    flags: List[str] = []
    # Identify non-None indices and values
    valid_indices = [i for i, v in enumerate(values) if v is not None and not np.isnan(v)]
    n = len(valid_indices)

    result: List[Optional[float]] = [None] * len(values)
    if n == 0:
        return result, flags

    if n == 1:
        result[valid_indices[0]] = 0.5
        flags.append("N=1 catalogue: percentile rank defaulted to 0.5")
        return result, flags

    valid_vals = np.array([values[i] for i in valid_indices], dtype=float)

    if n < config.min_careers_percentile:
        # Min-max scaling
        v_min = float(np.min(valid_vals))
        v_max = float(np.max(valid_vals))
        span = v_max - v_min
        flags.append(f"Catalogue size N={n} < {config.min_careers_percentile}; applied min-max scaling")

        for idx, val in zip(valid_indices, valid_vals):
            if span <= 1e-9:
                result[idx] = 0.5
            else:
                result[idx] = clamp((val - v_min) / span, 0.0, 1.0)
        return result, flags

    # Standard percentile ranking with average ties: (rank - 1) / (N - 1)
    ranks = rankdata(valid_vals, method="average")
    for idx, r in zip(valid_indices, ranks):
        result[idx] = clamp((r - 1.0) / (n - 1.0), 0.0, 1.0)

    return result, flags


def calculate_trend_component(
    growth: Optional[float],
    config: MarketSolverConfig = DEFAULT_CONFIG,
) -> Optional[float]:
    """trend = clamp((growth - g_min) / (g_max - g_min))."""
    if growth is None or np.isnan(growth):
        return None
    span = config.g_max - config.g_min
    if span <= 0.0:
        return 0.5
    return clamp((growth - config.g_min) / span, 0.0, 1.0)


def calculate_low_disruption(disruption_score: float) -> float:
    """low_disruption = 1 - D."""
    return clamp(1.0 - float(disruption_score), 0.0, 1.0)


def calculate_local_demand(
    career_record: CareerMarketRecord,
    regional_totals: Optional[RegionalTotals],
    student_region: Optional[str],
    config: MarketSolverConfig = DEFAULT_CONFIG,
) -> Tuple[Optional[float], Optional[float], str, List[str]]:
    """Compute local demand via location quotient LQ = (C_reg / C_nat) / (A_reg / A_nat).

    local_demand = clamp(LQ / lq_cap).
    If student_region is not given, or either regional figure is missing or zero, UNAVAILABLE.
    """
    flags: List[str] = []

    if not student_region:
        return None, None, "none", ["student_region not specified; local demand unavailable"]

    reg_key = student_region.strip().lower()

    if career_record.regional_postings is None:
        return None, None, "none", [f"No regional postings for career '{career_record.career_id}'"]

    # Match region key case-insensitively
    career_reg_map = {k.strip().lower(): v for k, v in career_record.regional_postings.items()}
    c_reg = career_reg_map.get(reg_key)

    if c_reg is None or c_reg <= 0:
        return None, None, "none", [f"Career postings in region '{student_region}' are missing or zero"]

    # Career national postings
    c_nat = sum(career_reg_map.values())
    if c_nat <= 0:
        return None, None, "none", ["Career national postings total zero; LQ undefined"]

    if regional_totals is None or regional_totals.national_total <= 0:
        return None, None, "none", ["Catalogue regional totals unavailable"]

    totals_map = {k.strip().lower(): v for k, v in regional_totals.region_totals.items()}
    a_reg = totals_map.get(reg_key)

    if a_reg is None or a_reg <= 0:
        return None, None, "none", [f"Total market postings in region '{student_region}' are missing or zero"]

    a_nat = float(regional_totals.national_total)

    # Compute Location Quotient
    lq = (c_reg / c_nat) / (a_reg / a_nat)
    scaled = clamp(lq / config.lq_cap, 0.0, 1.0)

    # Quality check
    if a_reg < config.local_min_postings:
        quality = "low"
        flags.append(f"Region '{student_region}' has only {a_reg:.0f} total postings (< {config.local_min_postings})")
    else:
        quality = "high" if c_reg >= 15 else "medium"

    return lq, scaled, quality, flags
