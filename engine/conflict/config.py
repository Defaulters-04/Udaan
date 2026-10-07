"""Configuration constants for the PRISM Conflict Index module."""

from dataclasses import dataclass, asdict
from typing import Dict, Any

from engine.config import DEFAULT_CONFIG as MASTER_CONFIG, ConflictConfig as MasterConflictConfig


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

    # Fix 1: Conflict index is diagnosis only and does NOT penalize scores or rankings.
    conflict_penalty_weight: float = 0.0

    # Negotiation slider default: 0.50 (equal student & parent balance)
    default_negotiation_alpha: float = 0.50

    # Compromise zone thresholds (Fix 8)
    min_student_fit_compromise: float = 0.50  # design assumption, unsourced
    min_parent_viability_compromise: float = 0.50  # design assumption, unsourced

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
