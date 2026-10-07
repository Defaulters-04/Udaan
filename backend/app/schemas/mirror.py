from typing import Literal, Union
from pydantic import BaseModel, ConfigDict
from app.schemas.assessment import LocalizedText


class StepOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: LocalizedText


class DomainOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: LocalizedText


class ScaleDimension(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Literal["risk", "relocation", "time"]
    gap: float
    weight: float
    kind: Literal["scale"]
    steps: list[StepOption]
    student_step: int
    parent_step: int


class PicksDimension(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Literal["domain"]
    gap: float
    weight: float
    kind: Literal["picks"]
    options: list[DomainOption]
    student_picks: list[str]
    parent_picks: list[str]
    parent_guess: Union[str, None]


Dimension = Union[ScaleDimension, PicksDimension]


class MirrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conflict_index: float
    dimensions: list[Dimension]
