"""Pydantic models for PRISM Conflict Index inputs and outputs."""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
import math


def _clamp(val: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a value to [low, high]."""
    return max(low, min(high, float(val)))


def _normalized_gap(val1: float, val2: float, scale_min: float, scale_max: float) -> float:
    """Compute normalized absolute gap between two values on a known scale."""
    if scale_max == scale_min:
        return 0.0
    return _clamp(abs(val1 - val2) / (scale_max - scale_min))


class DimensionConflict(BaseModel):
    """Conflict on a single shared dimension."""

    dimension: str = Field(
        ..., description="Dimension name: 'risk', 'domain', 'relocation', or 'time'"
    )
    student_value: float = Field(..., description="Student's value on this dimension")
    parent_value: float = Field(..., description="Parent's value on this dimension")
    gap: float = Field(..., ge=0.0, le=1.0, description="Normalized gap [0, 1]")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight in composite conflict")

    @property
    def weighted_gap(self) -> float:
        """Contribution to overall conflict (gap * weight)."""
        return self.gap * self.weight


class OverallConflictReport(BaseModel):
    """Family-wide conflict diagnosis across all shared dimensions."""

    # Individual dimension conflicts
    risk_conflict: DimensionConflict
    domain_conflict: DimensionConflict
    relocation_conflict: DimensionConflict
    time_conflict: DimensionConflict

    # Overall score (weighted sum of dimension gaps, normalized to [0, 1])
    overall_conflict: float = Field(
        ..., ge=0.0, le=1.0, description="Family conflict diagnosis: 0=aligned, 1=opposed"
    )

    # Flag for reporting / UI
    is_high_conflict: bool = Field(
        ..., description="True if any dimension gap exceeds conflict_threshold"
    )

    # Narrative explanations for UI (Family Mirror)
    diagnosis_summary: str = Field(
        default="", description="Human-readable family conflict diagnostic summary"
    )
    dimension_explanations: Dict[str, str] = Field(
        default_factory=dict, description="Detailed explanation per dimension"
    )

    @field_validator("overall_conflict")
    @classmethod
    def validate_sum(cls, v: float) -> float:
        return _clamp(v)


class CareerConflictReport(BaseModel):
    """Per-career conflict: how much student and parent disagree about THIS career route."""

    career_id: str = Field(..., description="Target career identifier")
    route_id: str = Field(..., description="Specific route/college pathway identifier")

    # Student's evaluation of this route on each dimension (0-1 fit scores)
    student_risk_fit: float = Field(..., ge=0.0, le=1.0)
    student_domain_fit: float = Field(..., ge=0.0, le=1.0)
    student_relocation_fit: float = Field(..., ge=0.0, le=1.0)
    student_time_fit: float = Field(..., ge=0.0, le=1.0)

    # Parent's evaluation of this route on each dimension (0-1 fit scores)
    parent_risk_fit: float = Field(..., ge=0.0, le=1.0)
    parent_domain_fit: float = Field(..., ge=0.0, le=1.0)
    parent_relocation_fit: float = Field(..., ge=0.0, le=1.0)
    parent_time_fit: float = Field(..., ge=0.0, le=1.0)

    # Per-dimension gaps (how much student and parent disagree about THIS route)
    risk_gap: float = Field(..., ge=0.0, le=1.0)
    domain_gap: float = Field(..., ge=0.0, le=1.0)
    relocation_gap: float = Field(..., ge=0.0, le=1.0)
    time_gap: float = Field(..., ge=0.0, le=1.0)

    # Overall conflict for this career route
    career_conflict: float = Field(
        ..., ge=0.0, le=1.0, description="Per-career conflict: 0=aligned, 1=opposed"
    )

    # Flag for high-conflict careers
    is_high_conflict: bool = Field(
        ..., description="True if any dimension gap exceeds conflict_threshold"
    )

    @field_validator("career_conflict")
    @classmethod
    def validate_career_conflict(cls, v: float) -> float:
        return _clamp(v)


class ConflictEvaluation(BaseModel):
    """Top-level output: family diagnosis + per-career conflict reports."""

    overall: OverallConflictReport
    career_conflicts: List[CareerConflictReport] = Field(
        default_factory=list, description="Conflict reports per evaluated career route"
    )

    # Summary statistics for reporting
    num_high_conflict_careers: int = Field(
        ..., ge=0, description="How many careers have is_high_conflict=True"
    )
    avg_career_conflict: float = Field(
        ..., ge=0.0, le=1.0, description="Mean conflict across all evaluated careers"
    )


# --- Input and Negotiation Models for API and UI Integration ---


class StudentConflictInput(BaseModel):
    """Input parameters for a student on shared conflict dimensions."""

    student_id: str = "student_1"
    risk_appetite: float = Field(0.5, ge=0.0, le=1.0, description="Risk tolerance [0, 1]")
    domain_preference: Dict[str, float] = Field(
        default_factory=dict, description="Ratings 1-5 for career domains"
    )
    relocation_willingness: float = Field(
        0.5, ge=0.0, le=1.0, description="Willingness to relocate [0, 1]"
    )
    max_years_to_income: float = Field(
        4.0, ge=0.0, description="Max acceptable years until first earning"
    )


class ParentConflictInput(BaseModel):
    """Input parameters for a parent on shared conflict dimensions."""

    risk: float = Field(0.5, ge=0.0, le=1.0, description="Parental risk tolerance [0, 1]")
    domain_ratings: Dict[str, float] = Field(
        default_factory=dict, description="Ratings 1-5 for career domains"
    )
    relocation_willingness: float = Field(
        0.5, ge=0.0, le=1.0, description="Willingness for child to relocate [0, 1]"
    )
    max_years_to_income: float = Field(
        4.0, ge=0.0, description="Max acceptable years until first earning"
    )


class RouteConflictInput(BaseModel):
    """Pathway / route specifications for per-career conflict evaluation."""

    career_id: str
    route_id: str
    career_risk: float = Field(0.5, ge=0.0, le=1.0, description="Inherent career risk profile [0, 1]")
    domain: str = Field("General", description="Domain classification (e.g. Technology & Engineering)")
    relocation_need: float = Field(0.5, ge=0.0, le=1.0, description="Degree of relocation required [0, 1]")
    years_to_first_income: float = Field(4.0, ge=0.0, description="Study + training years before earning")


class ConflictEvaluationRequest(BaseModel):
    """API request payload for evaluating overall family conflict and route-level conflict."""

    student: StudentConflictInput
    parent: ParentConflictInput
    routes: List[RouteConflictInput] = Field(default_factory=list)
    config: Optional[Dict[str, Any]] = None


class ScoredCareerInput(BaseModel):
    """A candidate career route scored by student fit and family viability."""

    career_id: str
    route_id: str
    career_name: Optional[str] = None
    student_fit: float = Field(..., ge=0.0, le=1.0, description="Student fit score [0, 1]")
    family_viability: float = Field(..., ge=0.0, le=1.0, description="Family affordability / parental viability [0, 1]")
    market_score: Any = Field(0.70, description="Job market score [0, 1] or 'NOT FOUND'")
    market_is_default: bool = Field(default=False, description="True if market score defaulted or NOT FOUND")
    career_risk: float = Field(0.50, ge=0.0, le=1.0)
    domain: str = "General"
    relocation_need: float = Field(0.50, ge=0.0, le=1.0)
    years_to_first_income: float = Field(4.0, ge=0.0)
    is_financially_viable: bool = True
    estimated_cost: float = Field(0.0, ge=0.0)


class CompromiseCareer(BaseModel):
    """A career analyzed for compromise balance between student and parent."""

    career_id: str
    route_id: str
    career_name: Optional[str] = None
    student_fit: float
    family_viability: float
    market_score: Any = 0.50
    market_is_default: bool = False
    fit_gap: float = Field(default=0.0, description="Per-career |Fit - Family| gap (Fix 2)")
    negotiated_score: float
    is_in_compromise_zone: bool
    is_pareto_optimal: bool
    is_financially_viable: bool
    conflict_flag: bool = False
    stretch: bool = False
    stretch_reasons: List[str] = Field(default_factory=list)
    market_tier: str = "stable"
    data_confidence: str = "high"
    summary_reason: str

    @property
    def career_conflict(self) -> float:
        """Alias for backward compatibility."""
        return self.fit_gap


class NegotiationRequest(BaseModel):
    """Request payload for Negotiation Explorer slider."""

    student: StudentConflictInput
    parent: ParentConflictInput
    careers: List[ScoredCareerInput]
    alpha: float = Field(
        0.5, ge=0.0, le=1.0, description="0=100% Parent Priority, 1=100% Student Priority, 0.5=Fair Balance"
    )
    min_student_fit: Optional[float] = None
    min_family_viability: Optional[float] = None
    config: Optional[Dict[str, Any]] = None


class NegotiationResponse(BaseModel):
    """Response payload for Negotiation Explorer."""

    alpha: float
    total_careers_evaluated: int
    compromise_zone_count: int
    ranked_careers: List[CompromiseCareer]
    compromise_zone_careers: List[CompromiseCareer]
    family_diagnosis: str
    balanced_pick_career_id: Optional[str] = None
    balanced_pick: Optional[CompromiseCareer] = None