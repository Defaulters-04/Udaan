"""PRISM Engine - Conflict Index Module.

Measures misalignment between student and parent vectors across shared dimensions:
risk appetite, domain preferences, relocation willingness, and time-to-income horizon.
Provides overall family diagnosis, per-career conflict evaluation, composite score blending,
and the Negotiation Explorer compromise zone solver.
"""

from .config import ConflictConfig, DEFAULT_CONFIG
from .models import (
    DimensionConflict,
    OverallConflictReport,
    CareerConflictReport,
    ConflictEvaluation,
    StudentConflictInput,
    ParentConflictInput,
    RouteConflictInput,
    ConflictEvaluationRequest,
    ScoredCareerInput,
    CompromiseCareer,
    NegotiationRequest,
    NegotiationResponse,
)
from .scores import (
    compute_overall_conflict,
    compute_career_conflict,
    evaluate_conflict,
    generate_conflict_explanations,
    compute_composite_score,
    evaluate_negotiation_slider,
)

__all__ = [
    "ConflictConfig",
    "DEFAULT_CONFIG",
    "DimensionConflict",
    "OverallConflictReport",
    "CareerConflictReport",
    "ConflictEvaluation",
    "StudentConflictInput",
    "ParentConflictInput",
    "RouteConflictInput",
    "ConflictEvaluationRequest",
    "ScoredCareerInput",
    "CompromiseCareer",
    "NegotiationRequest",
    "NegotiationResponse",
    "compute_overall_conflict",
    "compute_career_conflict",
    "evaluate_conflict",
    "generate_conflict_explanations",
    "compute_composite_score",
    "evaluate_negotiation_slider",
]
