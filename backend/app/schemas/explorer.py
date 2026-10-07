from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.assessment import LocalizedText


class RemedyText(BaseModel):
    model_config = ConfigDict(extra="forbid")

    en: str
    hi: Optional[str] = None


class Remedy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: RemedyText


class BlendPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float
    rank: int


class CareerBlocked(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gates: list[Literal["money", "academic"]]
    cause: Literal["no_route_data", "cost", "academic", "other"]
    remedies: list[Remedy]


class ExplorerCareer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: LocalizedText
    domain: str
    fit: Optional[float]
    viability: Optional[float]
    market: Optional[float]
    years_to_income: Optional[float]
    conflict: float
    in_compromise: bool
    blend: Optional[list[BlendPoint]]
    blocked: Optional[CareerBlocked]
    data_gaps: list[str]


class ExplorerSlider(BaseModel):
    model_config = ConfigDict(extra="forbid")

    positions: list[int]
    default: int


class ExplorerCompromise(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_fit: float
    min_viability: float


class ExplorerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slider: ExplorerSlider
    careers: list[ExplorerCareer]
    frontier: list[str]
    compromise: Optional[ExplorerCompromise]
