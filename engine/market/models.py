"""Pydantic v2 data models for PRISM Market Machine."""

from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class DemandDataPoint(BaseModel):
    """A single monthly job-postings observation."""

    month: str = Field(..., description="Month identifier in YYYY-MM format")
    count: float = Field(..., description="Observed job postings count")

    @field_validator("month")
    @classmethod
    def validate_month_format(cls, v: str) -> str:
        parts = v.strip().split("-")
        if len(parts) != 2 or len(parts[0]) != 4 or not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError(f"Month must be in YYYY-MM format, got '{v}'")
        m = int(parts[1])
        if not (1 <= m <= 12):
            raise ValueError(f"Month must be between 01 and 12, got '{v}'")
        return v.strip()


class DemandSeries(BaseModel):
    """Historical monthly postings demand series with audit trail."""

    points: List[DemandDataPoint] = Field(default_factory=list, description="Monthly postings sequence")
    source_label: str = Field(..., description="Origin of postings data (e.g. Adzuna India, Naukri)")
    fetched_at: str = Field(..., description="Snapshot retrieval date (YYYY-MM-DD)")

    @model_validator(mode="before")
    @classmethod
    def parse_flexible_series(cls, v: Any) -> Any:
        if isinstance(v, list):
            # Raw list of dicts passed directly
            return {"points": v, "source_label": "Unknown", "fetched_at": "1970-01-01"}
        if isinstance(v, dict):
            if "series" in v and "points" not in v:
                v["points"] = v.pop("series")
        return v


class CuratedTrend(BaseModel):
    """Fallback manual / curated growth trajectory."""

    growth_low: float = Field(..., description="Pessimistic year-on-year growth fraction")
    growth_central: float = Field(..., description="Central year-on-year growth fraction")
    growth_high: float = Field(..., description="Optimistic year-on-year growth fraction")
    source_label: str = Field(..., description="Source citation for curated trend estimate")

    @model_validator(mode="after")
    def validate_order(self) -> "CuratedTrend":
        if self.growth_low > self.growth_central or self.growth_central > self.growth_high:
            # Sort gracefully and record consistent order
            vals = sorted([self.growth_low, self.growth_central, self.growth_high])
            self.growth_low = vals[0]
            self.growth_central = vals[1]
            self.growth_high = vals[2]
        return self


class SalaryBands(BaseModel):
    """Annual salary percentiles in INR."""

    p10: float = Field(..., description="10th percentile annual gross starting salary in INR")
    p50: float = Field(..., description="Median / 50th percentile annual gross salary in INR")
    p90: float = Field(..., description="90th percentile annual gross salary in INR")
    source_label: str = Field(..., description="Source citation for salary percentiles")


class DisruptionProfile(BaseModel):
    """Automation and AI disruption risk profile."""

    model_config = ConfigDict(populate_by_name=True)

    score: float = Field(..., ge=0.0, le=1.0, alias="D", description="Disruption exposure index D in [0, 1]")
    rubric_version: str = Field(default="v1.0", description="Rubric evaluation version")
    human_reviewed: bool = Field(default=False, description="Whether score was human audited")

    @property
    def D(self) -> float:
        return self.score


class RegionalTotals(BaseModel):
    """Catalogue-wide regional total postings for Location Quotient normalisation."""

    region_totals: Dict[str, float] = Field(
        default_factory=dict, description="All-career postings per region"
    )
    national_total: float = Field(..., description="National total postings across all careers")
    source_label: str = Field(default="Aggregated Snapshots", description="Source of totals")
    fetched_at: str = Field(default="2026-10-01", description="Date totals were compiled")


class CareerMarketRecord(BaseModel):
    """Master market data record for an individual career pathway."""

    career_id: str = Field(..., description="Unique career identifier")
    name: str = Field(..., description="Human-readable career name")
    demand_series: Optional[DemandSeries] = Field(
        default=None, description="Monthly job postings series"
    )
    curated_trend: Optional[CuratedTrend] = Field(
        default=None, description="Curated fallback growth trend"
    )
    salary: SalaryBands = Field(..., description="Required salary percentiles")
    typical_route_cost: float = Field(
        ..., ge=0.0, description="Rupee total cost of typical route catalogue midpoint"
    )
    typical_duration_years: float = Field(
        default=4.0, ge=0.0, description="Typical preparation/college duration in years"
    )
    disruption: DisruptionProfile = Field(
        ..., description="Automation and AI disruption assessment"
    )
    regional_postings: Optional[Dict[str, float]] = Field(
        default=None, description="Optional postings counts per region/district for this career"
    )


class ComponentDetail(BaseModel):
    """Computed state for a single component of the market score."""

    name: str = Field(..., description="Component identifier")
    raw: Optional[float] = Field(None, description="Raw unscaled metric")
    scaled: Optional[float] = Field(None, description="Scaled component in [0, 1]")
    weight_nominal: float = Field(..., description="Configured default weight")
    weight_used: float = Field(..., description="Renormalized weight actually applied")
    available: bool = Field(..., description="Whether component had sufficient data to compute")
    quality: Literal["high", "medium", "low", "none"] = Field(
        ..., description="Quality / confidence tier for this component"
    )
    note: Optional[str] = Field(None, description="Diagnostic reason or calculation details")


class MarketReport(BaseModel):
    """Comprehensive market evaluation report for a single career."""

    career_id: str
    name: str
    F_market: float = Field(..., description="Pessimistic family-independent market score (0-100)")
    F_market_central: float = Field(..., description="Central market score (0-100)")
    F_market_optimistic: float = Field(..., description="Optimistic market score (0-100)")
    components: Dict[str, ComponentDetail]
    weights_used: Dict[str, float]
    g_low: Optional[float] = None
    g_central: Optional[float] = None
    g_high: Optional[float] = None
    trend_method: str
    volatility: float = Field(default=0.0, description="Forecast uncertainty (g_high - g_low)/2")
    risk_proxy: float = Field(
        ..., description="Suggested career risk R_c proxy: 0.5*D + 0.5*clamp(volatility/0.30)"
    )
    overall_confidence: Literal["high", "medium", "low"] = Field(
        ..., description="Overall confidence level"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Weighted fraction of high/medium components"
    )
    flags: List[str] = Field(default_factory=list, description="Audit and diagnostic warnings")
    source_labels: Dict[str, str] = Field(default_factory=dict, description="Audit source citations")
    fetched_at: Optional[str] = None
    explanation: str = Field(..., description="Template-based factual explanation")


class MarketCatalogueResult(BaseModel):
    """Catalogue-wide evaluation response."""

    reports: List[MarketReport]
    sorted_careers: List[MarketReport]
    low_confidence_careers: List[MarketReport]


# --- Hand-off & Sensitivity Models ---

class CareerScoreInput(BaseModel):
    """Input payload for multi-machine provisional hand-off."""

    career_id: str
    F_student: float = Field(..., ge=0.0, le=100.0)
    F_family: float = Field(..., ge=0.0, le=100.0)
    F_market: float = Field(..., ge=0.0, le=100.0)
    G_fin: int = Field(default=1, ge=0, le=1)
    G_acad: int = Field(default=1, ge=0, le=1)


class RankedCareer(BaseModel):
    """Final ranked career from provisional hand-off."""

    career_id: str
    rank: int
    F_student: float
    F_family: float
    F_market: float
    conflict_score: float
    composite_score: float
    final_score: float


class BlockedCareer(BaseModel):
    """Blocked career eliminated during provisional hand-off."""

    career_id: str
    reasons: List[str]


class HandoffResult(BaseModel):
    """Result of provisional hand-off ranking."""

    ranked: List[RankedCareer]
    blocked: List[BlockedCareer]


class CareerSensitivityResult(BaseModel):
    """Monte Carlo sensitivity stability metrics for a single career."""

    career_id: str
    top_3_stability_share: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of runs remaining in top 3"
    )
    rank_shift_3_or_more_share: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of runs with rank displacement >= 3"
    )


class SensitivityResponse(BaseModel):
    """Overall response for POST /market/sensitivity."""

    results: Dict[str, CareerSensitivityResult]
    runs: int
    seed: int
