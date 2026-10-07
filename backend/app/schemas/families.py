from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class RoleEnum(str, Enum):
    STUDENT = "student"
    PARENT = "parent"


class LangEnum(str, Enum):
    EN = "en"
    HI = "hi"


class CreateFamilyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: RoleEnum
    name: str
    lang: LangEnum

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: object) -> str:
        if not isinstance(v, str):
            raise ValueError("Name must be a string")
        trimmed = v.strip()
        if not (1 <= len(trimmed) <= 40):
            raise ValueError("Name must be between 1 and 40 characters")
        return trimmed


class JoinFamilyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: RoleEnum
    name: str
    lang: LangEnum

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: object) -> str:
        if not isinstance(v, str):
            raise ValueError("Name must be a string")
        trimmed = v.strip()
        if not (1 <= len(trimmed) <= 40):
            raise ValueError("Name must be between 1 and 40 characters")
        return trimmed


class CreateFamilyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family_code: str
    member_token: str
    role: str
    expires_at: str


class FamilyPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family_code: str
    open_role: Optional[RoleEnum] = None
    creator_name: str


class MemberSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str
    name: str


class StatusMemberSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str
    name: str
    done: bool


class JoinFamilyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family_code: str
    member_token: str
    role: str
    partner: MemberSummary
    expires_at: str


class FamilyStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family_code: str
    linked: bool
    you: StatusMemberSummary
    partner: Optional[StatusMemberSummary] = None
    expires_at: str
