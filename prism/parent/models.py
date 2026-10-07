"""Pydantic v2 data models for PRISM Parent Machine inputs and evaluation outputs."""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


def gl_to_risk(gl: float | int) -> float:
    """gl_to_risk(GL) = (GL - 13) / 34, with GL validated to 13..47."""
    gl_val = float(gl)
    if not (13.0 <= gl_val <= 47.0):
        raise ValueError(f"GL must be in range [13, 47], got {gl}")
    return (gl_val - 13.0) / 34.0


class SectorRatings(BaseModel):
    """Parental ratings for broad economic sectors (1 to 5 scale)."""

    govt: int = Field(..., ge=1, le=5, description="Preference for government/public sector")
    private: int = Field(..., ge=1, le=5, description="Preference for private/corporate sector")
    entrepreneurship: int = Field(..., ge=1, le=5, description="Preference for entrepreneurship/business")

    def get_rating(self, sector_name: str) -> Optional[int]:
        """Fetch rating by case-insensitive sector name."""
        key = sector_name.strip().lower()
        if key in ("govt", "government", "public", "public_sector"):
            return self.govt
        elif key in ("private", "corporate", "industry"):
            return self.private
        elif key in ("entrepreneurship", "startup", "business"):
            return self.entrepreneurship
        return None


class ParentProfile(BaseModel):
    """Parent profile model encapsulating family balance sheet, risk, and preferences.

    Units: All monetary values are in INR.
    Accepts both canonical attribute names and specification math symbols (S, M, M_inc, E_exist, L_max, Sal_p, T_p, rho_p, R_p).
    """

    model_config = ConfigDict(populate_by_name=True)

    savings: float = Field(..., ge=0.0, description="S: Total liquid savings available (INR)")
    monthly_surplus: float = Field(..., ge=0.0, description="M: Monthly uncommitted disposable cashflow (INR)")
    household_income: float = Field(..., description="M_inc: Gross monthly household income (INR)")
    existing_emis: float = Field(default=0.0, ge=0.0, description="E_exist: Existing monthly EMI commitments (INR)")
    loan_max: float = Field(..., ge=0.0, description="L_max: Maximum educational loan willingness/capacity (INR)")
    domain_ratings: Dict[str, Union[int, float]] = Field(default_factory=dict, description="Ratings for career domains (1-5)")
    sector_ratings: Union[SectorRatings, Dict[str, int]] = Field(
        ..., description="Ratings for sectors {govt, private, entrepreneurship} (1-5)"
    )
    min_salary: float = Field(..., description="Sal_p: Minimum acceptable annual starting salary (INR)")
    max_years_to_income: float = Field(..., ge=0.0, description="T_p: Maximum acceptable years until first income")
    relocation_willingness: float = Field(
        ..., ge=0.0, le=1.0, description="rho_p: Relocation willingness index (0-1)"
    )
    risk: float = Field(..., ge=0.0, le=1.0, description="R_p: Parental risk tolerance index (0-1)")
    dependents: Union[int, str] = Field(
        default=1, description="Number of dependents or dependent range (e.g. 1, 2, '1-2', '3+')"
    )

    @model_validator(mode="before")
    @classmethod
    def _map_math_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            alias_map = {
                "S": "savings",
                "M": "monthly_surplus",
                "M_inc": "household_income",
                "E_exist": "existing_emis",
                "L_max": "loan_max",
                "Sal_p": "min_salary",
                "T_p": "max_years_to_income",
                "rho_p": "relocation_willingness",
                "R_p": "risk",
                "D_dep": "dependents",
            }
            for alias, canonical in alias_map.items():
                if alias in data and canonical not in data:
                    data[canonical] = data[alias]
        return data

    @field_validator("sector_ratings", mode="before")
    @classmethod
    def parse_sector_ratings(cls, v: Any) -> Any:
        if isinstance(v, dict):
            norm = {str(k).lower(): val for k, val in v.items()}
            return SectorRatings(
                govt=int(norm.get("govt", 3)),
                private=int(norm.get("private", 3)),
                entrepreneurship=int(norm.get("entrepreneurship", 3)),
            )
        return v

    @field_validator("domain_ratings")
    @classmethod
    def validate_domain_ratings(cls, v: Dict[str, Union[int, float]]) -> Dict[str, Union[int, float]]:
        for dom, rating in v.items():
            r = float(rating)
            if not (1.0 <= r <= 5.0):
                raise ValueError(f"Rating for domain '{dom}' must be between 1 and 5, got {rating}")
        return v

    @classmethod
    def from_gl(cls, gl: float | int, **kwargs) -> "ParentProfile":
        """Instantiate ParentProfile computing risk R_p from Gardner-Likert GL score."""
        r_p = gl_to_risk(gl)
        return cls(risk=r_p, **kwargs)

    # Shorthand property accessors matching math specification
    @property
    def S(self) -> float:
        return self.savings

    @property
    def M(self) -> float:
        return self.monthly_surplus

    @property
    def M_inc(self) -> float:
        return self.household_income

    @property
    def E_exist(self) -> float:
        return self.existing_emis

    @property
    def L_max(self) -> float:
        return self.loan_max

    @property
    def Sal_p(self) -> float:
        return self.min_salary

    @property
    def T_p(self) -> float:
        return self.max_years_to_income

    @property
    def rho_p(self) -> float:
        return self.relocation_willingness

    @property
    def R_p(self) -> float:
        return self.risk


class Route(BaseModel):
    """Educational pathway route towards a target career.

    Units: All monetary values are in INR.
    Accepts both canonical attribute names and specification math symbols (T, L, E_exam, G, Y, Y1, t_r, R_c, rho_c).
    """

    model_config = ConfigDict(populate_by_name=True)

    career_id: str = Field(..., description="Unique identifier of target career")
    route_id: str = Field(..., description="Unique identifier of route/college pathway")
    tuition: float = Field(..., ge=0.0, description="T: Total tuition fee across duration (INR)")
    living: float = Field(..., ge=0.0, description="L: Total living and hostel cost across duration (INR)")
    exam_equipment: float = Field(default=0.0, ge=0.0, description="E_exam: Exam, prep, and equipment fees (INR)")
    grant: float = Field(default=0.0, ge=0.0, description="G: Scholarships and grants received (INR)")
    duration_years: float = Field(..., ge=0.0, description="Y: Duration of educational pathway in years")
    starting_salary: float = Field(..., description="Y1: Expected annual gross starting salary (INR)")
    years_to_first_income: float = Field(..., description="t_r: Years until student earns first income")
    career_risk: float = Field(..., ge=0.0, le=1.0, description="R_c: Career pathway risk index (0-1)")
    relocation_need: float = Field(..., ge=0.0, le=1.0, description="rho_c: Relocation requirement index (0-1)")
    domain: str = Field(..., description="Domain/discipline name")
    sector: str = Field(..., description="Sector {govt, private, entrepreneurship}")
    g_acad: int = Field(default=1, ge=0, le=1, description="Academic gate eligibility flag (0 or 1)")

    @model_validator(mode="before")
    @classmethod
    def _map_math_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            alias_map = {
                "T": "tuition",
                "L": "living",
                "E_exam": "exam_equipment",
                "G": "grant",
                "Y": "duration_years",
                "Y1": "starting_salary",
                "t_r": "years_to_first_income",
                "R_c": "career_risk",
                "rho_c": "relocation_need",
            }
            for alias, canonical in alias_map.items():
                if alias in data and canonical not in data:
                    data[canonical] = data[alias]
        return data

    # Shorthand property accessors matching math specification
    @property
    def T(self) -> float:
        return self.tuition

    @property
    def L(self) -> float:
        return self.living

    @property
    def E_exam(self) -> float:
        return self.exam_equipment

    @property
    def G(self) -> float:
        return self.grant

    @property
    def Y(self) -> float:
        return self.duration_years

    @property
    def Y1(self) -> float:
        return self.starting_salary

    @property
    def t_r(self) -> float:
        return self.years_to_first_income

    @property
    def R_c(self) -> float:
        return self.career_risk

    @property
    def rho_c(self) -> float:
        return self.relocation_need


class SubScores(BaseModel):
    """Fine-grained sub-score components across financial and aspirational dimensions."""

    f_budget: float = Field(..., ge=0.0, le=1.0, description="Budget score in [0, 1]")
    f_repay_p: float = Field(..., ge=0.0, le=1.0, description="Parent repayment burden score in [0, 1]")
    f_dsr: float = Field(..., ge=0.0, le=1.0, description="Debt service ratio score in [0, 1]")
    f_payback: float = Field(..., ge=0.0, le=1.0, description="Payback horizon score in [0, 1]")
    f_domain: float = Field(..., ge=0.0, le=1.0, description="Domain alignment score in [0, 1]")
    f_sector: float = Field(..., ge=0.0, le=1.0, description="Sector alignment score in [0, 1]")
    f_salary: float = Field(..., ge=0.0, le=1.0, description="Salary expectation score in [0, 1]")
    f_time: float = Field(..., ge=0.0, le=1.0, description="Time to income alignment score in [0, 1]")
    f_location: float = Field(..., ge=0.0, le=1.0, description="Relocation willingness alignment in [0, 1]")


class ViabilityReport(BaseModel):
    """Comprehensive viability evaluation for a single educational route."""

    career_id: str
    route_id: str
    cost_net: float = Field(..., description="N_r: Net educational cost in INR")
    cash_available: float = Field(..., description="A_cash: Family cash capacity in INR")
    loan_needed: float = Field(..., description="L_need: Education loan required in INR")
    emi: float = Field(..., description="EMI: Monthly loan repayment in INR")
    repayment_burden: float = Field(..., description="RB: Repayment burden ratio (E_exist + EMI)/M_inc")
    debt_service_ratio: float = Field(..., description="DSR: Debt service ratio (12*EMI)/Y1")
    payback_years: float = Field(..., description="Payback: Cost recovery horizon in years")
    g_fin: int = Field(..., ge=0, le=1, description="Financial feasibility gate (0 or 1)")
    g_acad: int = Field(default=1, ge=0, le=1, description="Academic eligibility gate (0 or 1)")
    gate_cleared: int = Field(..., ge=0, le=1, description="Combined gate G = G_fin * g_acad (0 or 1)")
    sub_scores: SubScores
    f_financial: float = Field(..., ge=0.0, le=100.0, description="Financial composite score (0-100)")
    f_aspiration: float = Field(..., ge=0.0, le=100.0, description="Aspiration alignment score (0-100)")
    f_risk: float = Field(..., ge=0.0, le=100.0, description="Risk tolerance alignment score (0-100)")
    f_family: float = Field(..., ge=0.0, le=100.0, description="Total composite family score (0-100)")
    funding_gap: float = Field(default=0.0, ge=0.0, description="max(0, L_need - L_max), shown when blocked")
    block_reasons: List[str] = Field(default_factory=list, description="Specific gate failures and deficits")
    warnings: List[str] = Field(default_factory=list, description="Diagnostic and edge-case warnings")

    # Shorthand properties matching specification
    @property
    def N_r(self) -> float:
        return self.cost_net

    @property
    def A_cash(self) -> float:
        return self.cash_available

    @property
    def L_need(self) -> float:
        return self.loan_needed

    @property
    def EMI(self) -> float:
        return self.emi

    @property
    def RB(self) -> float:
        return self.repayment_burden

    @property
    def DSR(self) -> float:
        return self.debt_service_ratio

    @property
    def Payback(self) -> float:
        return self.payback_years

    @property
    def G_fin(self) -> int:
        return self.g_fin

    @property
    def F_financial(self) -> float:
        return self.f_financial

    @property
    def F_aspiration(self) -> float:
        return self.f_aspiration

    @property
    def F_risk(self) -> float:
        return self.f_risk

    @property
    def F_family(self) -> float:
        return self.f_family


class BlockedRouteInfo(BaseModel):
    """Details and constructive remediation advice for a financially blocked route."""

    career_id: str
    route_id: str
    cost_net: float
    funding_gap: float
    block_reasons: List[str]
    suggestion: str
    shortfall_grant_needed: float


class CareerEvaluation(BaseModel):
    """Aggregated parent-side evaluation for a career across its alternative routes."""

    career_id: str
    best_route: Optional[ViabilityReport] = None
    f_family_career: float = Field(..., ge=0.0, le=100.0, description="Max F_family across available routes")
    alternatives: List[ViabilityReport] = Field(default_factory=list, description="Routes sorted by F_family descending")

    @property
    def F_family_career(self) -> float:
        return self.f_family_career


class ParentEvaluationRequest(BaseModel):
    """Payload for POST /parent/evaluate."""

    profile: ParentProfile
    routes: List[Route]
    config: Optional[Dict[str, Any]] = None


class ParentEvaluationResponse(BaseModel):
    """Response returned by POST /parent/evaluate."""

    career_results: Dict[str, CareerEvaluation]
    reports: List[ViabilityReport]
    blocked_list: List[BlockedRouteInfo]
