"""Monte Carlo sensitivity analysis for PRISM Market Machine."""

from typing import List, Dict, Optional
import numpy as np

from .config import MarketSolverConfig, DEFAULT_CONFIG
from .models import (
    CareerMarketRecord,
    RegionalTotals,
    CareerSensitivityResult,
    SensitivityResponse,
)
from .scores import evaluate_market_catalogue


def run_market_sensitivity(
    careers: List[CareerMarketRecord],
    config: MarketSolverConfig = DEFAULT_CONFIG,
    n: int = 1000,
    seed: int = 0,
    regional_totals: Optional[RegionalTotals] = None,
    student_region: Optional[str] = None,
) -> SensitivityResponse:
    """Perturb F_market weights by uniform +/-20%, renormalize, and calculate stability shares.

    Computes:
    - top_3_stability_share: fraction of runs career remains in top 3 by F_market.
    - rank_shift_3_or_more_share: fraction of runs where rank changes by >= 3 compared to baseline.
    """
    if not careers:
        return SensitivityResponse(results={}, runs=n, seed=seed)

    # 1. Evaluate baseline catalogue
    base_res = evaluate_market_catalogue(careers, regional_totals, student_region, config)
    base_ranks = {rep.career_id: rank for rank, rep in enumerate(base_res.sorted_careers, 1)}

    # Extract static pre-computed component scores and availability per career
    career_ids = [rep.career_id for rep in base_res.reports]
    comp_names = ["demand_level", "trend", "pay_yield", "low_disruption", "local_demand"]
    base_weights = np.array([
        config.w_demand_level,
        config.w_trend,
        config.w_pay_yield,
        config.w_low_disruption,
        config.w_local_demand,
    ], dtype=float)

    # Matrix of scaled component values (num_careers x 5)
    # and boolean availability matrix (num_careers x 5)
    num_careers = len(career_ids)
    scores_matrix = np.zeros((num_careers, 5), dtype=float)
    avail_matrix = np.zeros((num_careers, 5), dtype=bool)

    for i, rep in enumerate(base_res.reports):
        for j, cname in enumerate(comp_names):
            comp = rep.components[cname]
            if comp.available and comp.scaled is not None:
                scores_matrix[i, j] = comp.scaled
                avail_matrix[i, j] = True

    # 2. Monte Carlo simulations with seeded RNG
    rng = np.random.default_rng(seed)
    top_3_counts = np.zeros(num_careers, dtype=int)
    rank_shift_counts = np.zeros(num_careers, dtype=int)

    base_rank_array = np.array([base_ranks[cid] for cid in career_ids], dtype=int)

    perturb_factor = config.sensitivity_perturbation  # 0.20

    for _ in range(n):
        # Draw random perturbations in [1 - 0.20, 1 + 0.20]
        multipliers = rng.uniform(1.0 - perturb_factor, 1.0 + perturb_factor, size=5)
        perturbed_w = base_weights * multipliers

        # Renormalize weights per career based on available components
        # avail_matrix has shape (num_careers, 5)
        # Compute effective weights
        eff_weights = avail_matrix * perturbed_w  # broadcasts to (num_careers, 5)
        weight_sums = eff_weights.sum(axis=1, keepdims=True)
        # Avoid division by zero
        weight_sums = np.where(weight_sums <= 0, 1.0, weight_sums)
        norm_weights = eff_weights / weight_sums

        # F_market scores for this run: sum(norm_weights * scores_matrix) * 100
        run_scores = (norm_weights * scores_matrix).sum(axis=1) * 100.0

        # Determine ranks descending: argsort of (-run_scores)
        order = np.argsort(-run_scores)
        run_ranks = np.empty(num_careers, dtype=int)
        run_ranks[order] = np.arange(1, num_careers + 1)

        # Check top 3
        top_3_counts += (run_ranks <= 3)

        # Check rank displacement >= threshold
        rank_shift_counts += (np.abs(run_ranks - base_rank_array) >= config.sensitivity_rank_change_threshold)

    results: Dict[str, CareerSensitivityResult] = {}
    for i, cid in enumerate(career_ids):
        results[cid] = CareerSensitivityResult(
            career_id=cid,
            top_3_stability_share=round(float(top_3_counts[i] / n), 4),
            rank_shift_3_or_more_share=round(float(rank_shift_counts[i] / n), 4),
        )

    return SensitivityResponse(results=results, runs=n, seed=seed)
