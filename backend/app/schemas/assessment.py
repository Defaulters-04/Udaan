from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class LocalizedText(BaseModel):
    model_config = ConfigDict(extra="forbid")

    en: str
    hi: str


class QuestionOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: LocalizedText


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    prompt: LocalizedText
    required: bool
    options: Optional[list[QuestionOption]] = None
    min: Optional[int] = None
    max: Optional[int] = None
    min_label: Optional[LocalizedText] = None
    max_label: Optional[LocalizedText] = None
    max_length: Optional[int] = None
    placeholder: Optional[LocalizedText] = None


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: LocalizedText
    questions: list[dict[str, Any]]


class QuestionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    sections: list[Section]


class ProgressResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: dict[str, Any]
    submitted: bool


class PutAnswersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: dict[str, Any]


class PutAnswersResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answered: int
    total: int


class SubmitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submitted: bool
