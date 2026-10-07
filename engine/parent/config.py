"""Configuration constants for the PRISM Parent Machine solver and scoring engine."""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass(frozen=True)
class ParentSolverConfig:
    """Configurable parameters for PRISM financial constraint solver and family scores.

    All constants are parameterised here to facilitate sensitivity analyses (+/-20%)
    and avoid hardcoded values anywhere in solver logic.
    """

    # Cash and savings liquidation shares
    savings_share: float = 0.50
    surplus_share: float = 0.25

    # Loan terms
    annual_loan_rate: float = 0.10
    loan_term_months: int = 84

    # Hard gate thresholds for G_fin
    rb_gate_max: float = 0.50
    dsr_gate_max: float = 0.20

    # Soft repayment scoring thresholds
    rb_comfort_threshold: float = 0.30
    rb_penalty_range: float = 0.20

    dsr_comfort_threshold: float = 0.10
    dsr_penalty_range: float = 0.10

    # Payback parameters
    payback_income_share: float = 0.20
    payback_horizon_years: float = 8.0

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

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParentSolverConfig":
        """Instantiate configuration from dictionary, ignoring extraneous keys."""
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def with_overrides(self, **kwargs) -> "ParentSolverConfig":
        """Return a new config instance with selected parameters overridden."""
        current = self.to_dict()
        current.update(kwargs)
        return self.from_dict(current)


DEFAULT_CONFIG = ParentSolverConfig()
