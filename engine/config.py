"""Centralized configuration for the UDAAN PRISM Engine.

Every weight, threshold, and cutoff across student fit, parent viability,
conflict diagnosis, and market tiers lives in this single config file.
No numbers are hardcoded in scoring logic.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any


# ---------------------------------------------------------------------------
# 1. Student Fit Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StudentFitConfig:
    # Scale normalization bounds
    scale_min: float = 0.0
    scale_max: float = 1.0

    # RIASEC 6-factor interest model dimensions
    riasec_dimensions: tuple[str, ...] = ("R", "I", "A", "S", "E", "C")

    # Core aptitude dimensions
    aptitude_dimensions: tuple[str, ...] = ("logical", "numerical", "verbal", "spatial")

    # Stage-specific scoring weights: w_I, w_A, w_S, w_P
    # School stage skips SkillFit for early learners
    stage_weights_school: dict[str, float] = field(
        default_factory=lambda: {
            "w_I": 0.55,
            "w_A": 0.35,
            "w_S": 0.00,
            "w_P": 0.10,
        }
    )
    # College stage incorporates acquired domain skills
    stage_weights_college: dict[str, float] = field(
        default_factory=lambda: {
            "w_I": 0.40,
            "w_A": 0.30,
            "w_S": 0.20,
            "w_P": 0.10,
        }
    )

    # Stretch career threshold (Fix 3)
    # Aptitude shortfall ratio = sum(u_j * max(0, c_j - a_j)) / sum(u_j * c_j)
    stretch_shortfall_ratio: float = 0.20  # design assumption, unsourced

    # InterestFit blended weights (Fix 6)
    w_pearson: float = 0.50  # design assumption, unsourced
    w_overlap: float = 0.50  # design assumption, unsourced

    # Flat RIASEC threshold (Fix 6)
    riasec_flat_std_threshold: float = 0.01  # design assumption, unsourced

    # SWOT Analysis configuration
    swot_importance_criteria: str = "mean"
    swot_max_weaknesses: int = 3


# ---------------------------------------------------------------------------
# 2. Parent Solver & Family Viability Configuration (Fix 7)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ParentSolverConfig:
    # Cash and savings liquidation shares
    savings_share: float = 0.50
    surplus_share: float = 0.25

    # Loan terms
    annual_loan_rate: float = 0.10
    loan_term_months: int = 84

    # Hard gate thresholds for G_fin
    rb_gate_max: float = 0.50  # design assumption, unsourced, verify against bank lending norms
    dsr_gate_max: float = 0.20  # design assumption, unsourced, verify against bank lending norms

    # Soft repayment scoring thresholds
    rb_comfort_threshold: float = 0.30  # design assumption, unsourced, verify against bank lending norms
    rb_penalty_range: float = 0.20  # design assumption, unsourced, verify against bank lending norms

    dsr_comfort_threshold: float = 0.10  # design assumption, unsourced, verify against bank lending norms
    dsr_penalty_range: float = 0.10  # design assumption, unsourced, verify against bank lending norms

    # Payback parameters
    payback_income_share: float = 0.20  # design assumption, unsourced, verify against bank lending norms
    payback_horizon_years: float = 8.0  # design assumption, unsourced, verify against bank lending norms

    # Weights for F_financial (sum to 1.00)
    w_budget: float = 0.35
    w_repay_p: float = 0.25
    w_dsr: float = 0.25
    w_payback: float = 0.15

    # Weights for F_aspiration (sum to 1.00)
    w_domain: float = 0.30
    w_sector: float = 0.15
    w_salary: float = 0.20
    w_time: float = 0.20
    w_location: float = 0.15

    # Composite weights for F_family (sum to 1.00)
    w_financial: float = 0.50
    w_aspiration: float = 0.30
    w_risk: float = 0.20

    # Domain & sector rating scales
    rating_min: float = 1.0
    rating_max: float = 5.0

    # Gardner-Likert parental risk scale
    gl_min: float = 13.0
    gl_max: float = 47.0


# ---------------------------------------------------------------------------
# 3. Market Tiers & Evaluation Configuration (Fix 5)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MarketTiersConfig:
    # Growth / velocity thresholds
    velocity_rising_threshold: float = 0.05  # design assumption, unsourced
    velocity_declining_threshold: float = -0.05  # design assumption, unsourced

    # Raw demand postings thresholds
    demand_rising_threshold: float = 500.0  # design assumption, unsourced
    demand_declining_threshold: float = 100.0  # design assumption, unsourced

    # Disruption exposure thresholds (lower disruption is better)
    disruption_low_threshold: float = 0.35  # design assumption, unsourced
    disruption_high_threshold: float = 0.65  # design assumption, unsourced

    # Points lookup table for tiers
    tier_points: dict[str, dict[str, float]] = field(
        default_factory=lambda: {
            "demand": {
                "rising": 100.0,   # design assumption, unsourced
                "stable": 60.0,    # design assumption, unsourced
                "declining": 20.0, # design assumption, unsourced
            },
            "velocity": {
                "rising": 100.0,   # design assumption, unsourced
                "stable": 60.0,    # design assumption, unsourced
                "declining": 20.0, # design assumption, unsourced
            },
            "disruption": {
                "low": 100.0,      # design assumption, unsourced
                "medium": 60.0,    # design assumption, unsourced
                "high": 20.0,      # design assumption, unsourced
            },
        }
    )

    # Weights for aggregating tier points into a tiebreaker score
    w_tier_demand: float = 0.40  # design assumption, unsourced
    w_tier_velocity: float = 0.35  # design assumption, unsourced
    w_tier_disruption: float = 0.25  # design assumption, unsourced

    # Confidence audit cutoffs
    confidence_high_threshold: float = 0.80
    confidence_medium_threshold: float = 0.50
    max_snapshot_age_days: int = 180

    # Local demand / LQ settings
    lq_cap: float = 2.0
    local_min_postings: int = 30
    cost_floor: float = 50000.0
    g_min: float = -0.30
    g_max: float = 0.30

    # Forecast settings
    prediction_interval_level: float = 0.80
    forecast_horizon_months: int = 12
    min_points_ets: int = 24
    min_points_ols: int = 12
    min_points_seasonal: int = 36
    max_gap_fill_months: int = 2

    # Volatility / risk proxy settings
    volatility_scale: float = 0.30
    risk_proxy_weight_d: float = 0.50
    risk_proxy_weight_vol: float = 0.50


# ---------------------------------------------------------------------------
# 4. Conflict Index & Negotiation Configuration (Fix 1, 2, 8)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ConflictConfig:
    # Weights for overall family conflict dimensions (must sum to 1.00)
    w_risk: float = 0.25
    w_domain: float = 0.25
    w_relocation: float = 0.25
    w_time: float = 0.25

    # Threshold for flagging high conflict (overall or per dimension)
    conflict_threshold: float = 0.40

    # Negotiation slider default: 0.50 (equal student & parent balance)
    default_negotiation_alpha: float = 0.50

    # Compromise zone thresholds (Fix 8)
    min_student_fit_compromise: float = 50.0  # design assumption, unsourced
    min_parent_viability_compromise: float = 50.0  # design assumption, unsourced


# ---------------------------------------------------------------------------
# 5. Missing Data Configuration (Fix 4)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MissingDataConfig:
    # Max fraction of dropped weight to qualify for high/medium data confidence
    data_confidence_high_max_dropped: float = 0.15  # design assumption, unsourced
    data_confidence_med_max_dropped: float = 0.40  # design assumption, unsourced


# ---------------------------------------------------------------------------
# Master Engine Config Dataclass
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EngineConfig:
    student_fit: StudentFitConfig = field(default_factory=StudentFitConfig)
    parent: ParentSolverConfig = field(default_factory=ParentSolverConfig)
    market: MarketTiersConfig = field(default_factory=MarketTiersConfig)
    conflict: ConflictConfig = field(default_factory=ConflictConfig)
    missing_data: MissingDataConfig = field(default_factory=MissingDataConfig)


DEFAULT_CONFIG = EngineConfig()
