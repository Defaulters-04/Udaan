from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict

from app.schemas.assessment import LocalizedText
from app.schemas.explorer import CareerBlocked, RemedyText


class RouteCostParts(BaseModel):
    tuition: Optional[float] = None
    living: Optional[float] = None
    entrance: Optional[float] = None

    model_config = ConfigDict(extra="forbid")


class RouteItem(BaseModel):
    id: str
    label: str
    years: Optional[float] = None
    total_cost: Optional[float] = None
    cost_parts: RouteCostParts
    cost_status: str
    is_best: bool

    model_config = ConfigDict(extra="forbid")


class EntrySalary(BaseModel):
    min: Optional[float] = None
    median: Optional[float] = None
    max: Optional[float] = None
    unit: Literal["inr_per_year"] = "inr_per_year"
    source: str

    model_config = ConfigDict(extra="forbid")


class DemandInfo(BaseModel):
    signal: Literal["positive", "neutral", "negative"]
    source: str

    model_config = ConfigDict(extra="forbid")


class ScholarshipItem(BaseModel):
    name: str
    url: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class GrowthAreaItem(BaseModel):
    id: str
    text: RemedyText

    model_config = ConfigDict(extra="forbid")


class FamilyMoney(BaseModel):
    loan_need: Optional[float] = None
    monthly_emi: Optional[float] = None

    model_config = ConfigDict(extra="forbid")


class CareerDetailResponse(BaseModel):
    id: str
    name: LocalizedText
    domain: str
    fit: Optional[float] = None
    viability: Optional[float] = None
    market: Optional[float] = None
    years_to_income: Optional[float] = None
    conflict: float
    in_compromise: bool
    blocked: Optional[CareerBlocked] = None
    routes: list[RouteItem]
    entry_salary: Optional[EntrySalary] = None
    demand: Optional[DemandInfo] = None
    exams: list[str]
    scholarships: Optional[list[ScholarshipItem]] = None
    growth_areas: Optional[list[GrowthAreaItem]] = None
    family_money: Optional[FamilyMoney] = None
    data_gaps: list[str]

    model_config = ConfigDict(extra="forbid")
