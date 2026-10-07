"""Configuration constants for the PRISM Conflict Index module."""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass(frozen=True)
class ConflictConfig:
    """Configurable weights and thresholds for the PRISM Conflict Index.

    All constants are parameterised here to facilitate sensitivity analyses
    and avoid hardcoded values anywhere in conflict evaluation logic.
    """

    # Weights for overall & per-career conflict dimensions (must sum to 1.00)
    w_risk: float = 0.25
    w_domain: float = 0.25
    w_relocation: float = 0.25
    w_time: float = 0.25

    # Threshold for flagging high conflict (per dimension or overall)
    conflict_threshold: float = 0.40

    # Composite penalty weight when blending into final career ranking
    # composite_score = (1 - alpha_conflict) * base_score - alpha_conflict * conflict
    # or score_with_penalty = base_score * (1.0 - penalty_weight * career_conflict)
    conflict_penalty_weight: float = 0.15

    # Negotiation slider default: 0.50 (equal student & parent balance)
    # alpha in [0, 1] where alpha=1.0 is 100% student fit, alpha=0.0 is 100% parent viability
    default_negotiation_alpha: float = 0.50

    # Compromise zone thresholds: careers where both sides achieve at least minimum acceptability
    min_student_fit_compromise: float = 0.50
    min_parent_viability_compromise: float = 0.50

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConflictConfig":
        """Instantiate configuration from dictionary, ignoring extraneous keys."""
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def with_overrides(self, **kwargs) -> "ConflictConfig":
        """Return a new config instance with selected parameters overridden."""
        current = self.to_dict()
        current.update(kwargs)
        return self.from_dict(current)


DEFAULT_CONFIG = ConflictConfig()
