"""Configuration parameters for the PRISM Market Machine engine."""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any

from engine.config import DEFAULT_CONFIG as MASTER_CONFIG, MarketTiersConfig as MasterMarketConfig


@dataclass(frozen=True)
class MarketSolverConfig:
    """Configurable parameters for PRISM Market Machine scoring, tiers, and forecasting.

    All constants live in this dataclass and are passed into pure functions,
    never hardcoded.
    """

    # Component weights (sum to 1.00 when all 5 available)
    w_demand_level: float = 0.25
    w_trend: float = 0.30
    w_pay_yield: float = 0.20
    w_low_disruption: float = 0.15
    w_local_demand: float = 0.10

    # Trend scaling bounds
    g_min: float = -0.30
    g_max: float = 0.30

    # Tier thresholds (Fix 5)
    velocity_rising_threshold: float = 0.05  # design assumption, unsourced
    velocity_declining_threshold: float = -0.05  # design assumption, unsourced
    demand_rising_threshold: float = 500.0  # design assumption, unsourced
    demand_declining_threshold: float = 100.0  # design assumption, unsourced
    disruption_low_threshold: float = 0.35  # design assumption, unsourced
    disruption_high_threshold: float = 0.65  # design assumption, unsourced

    # Points lookup table for tiers (Fix 5)
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

    # Weights for aggregating tier points into tiebreaker score (Fix 5)
    w_tier_demand: float = 0.40  # design assumption, unsourced
    w_tier_velocity: float = 0.35  # design assumption, unsourced
    w_tier_disruption: float = 0.25  # design assumption, unsourced

    # Forecast settings
    prediction_interval_level: float = 0.80  # 80% interval (alpha = 0.20)
    forecast_horizon_months: int = 12
    min_points_ets: int = 24
    min_points_ols: int = 12
    min_points_seasonal: int = 36
    max_gap_fill_months: int = 2

    # Pay yield settings
    cost_floor: float = 50000.0  # INR minimum cost floor to prevent division blowup

    # Local demand settings
    lq_cap: float = 2.0  # Location quotient cap
    local_min_postings: int = 30  # Threshold below which local confidence is flagged low

    # Risk proxy & volatility settings
    volatility_scale: float = 0.30
    risk_proxy_weight_d: float = 0.50
    risk_proxy_weight_vol: float = 0.50

    # Snapshot data & confidence settings
    max_snapshot_age_days: int = 180
    confidence_high_threshold: float = 0.80
    confidence_medium_threshold: float = 0.50
    min_careers_percentile: int = 5

    # Hand-off composite settings (Fix 1: conflict_penalty is deleted / 0.0)
    w_handoff_student: float = 0.50
    w_handoff_family: float = 0.50
    w_handoff_market: float = 0.00
    conflict_penalty: float = 0.00

    # Sensitivity analysis defaults
    sensitivity_perturbation: float = 0.20
    sensitivity_runs: int = 1000
    sensitivity_rank_change_threshold: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketSolverConfig":
        """Instantiate configuration from dictionary, ignoring extraneous keys."""
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def with_overrides(self, **kwargs) -> "MarketSolverConfig":
        """Return a new config instance with selected parameters overridden."""
        current = self.to_dict()
        current.update(kwargs)
        return self.from_dict(current)


DEFAULT_CONFIG = MarketSolverConfig()
