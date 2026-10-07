"""Configuration parameters for the PRISM Market Machine engine."""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass(frozen=True)
class MarketSolverConfig:
    """Configurable parameters for PRISM Market Machine scoring and forecasting.

    All constants live in this dataclass and are passed into pure functions,
    never hardcoded. Supports +/-20% sensitivity perturbations.
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
    lq_cap: float = 2.0  # Location quotient cap (LQ=1 -> 0.5, LQ>=2 -> 1.0)
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

    # Hand-off composite settings
    w_handoff_student: float = 0.45
    w_handoff_family: float = 0.35
    w_handoff_market: float = 0.20
    conflict_penalty: float = 0.10

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
