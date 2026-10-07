from typing import Optional
from fastapi import APIRouter, Header, HTTPException, status

from app.assessment.bank import get_public_sections
from app.assessment.validate import validate_answers_payload
from app.schemas.assessment import (
    ProgressResponse,
    PutAnswersRequest,
    PutAnswersResponse,
    QuestionsResponse,
    SubmitResponse,
)
from app.store.families import family_store

router = APIRouter(prefix="/families/{family_code}/assessment", tags=["assessment"])


def raise_api_error(status_code: int, code: str, message: str, **kwargs) -> None:
    detail = {"code": code, "message": message}
    detail.update(kwargs)
    raise HTTPException(status_code=status_code, detail=detail)


@router.get("/questions", response_model=QuestionsResponse)
def get_assessment_questions(
    family_code: str,
    x_member_token: Optional[str] = Header(None, alias="X-Member-Token"),
) -> QuestionsResponse:
    err, family, member = family_store.authenticate_student(family_code, x_member_token)
    if err == "invalid_token":
        raise_api_error(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Invalid member token")
    if err == "family_not_found":
        raise_api_error(status.HTTP_404_NOT_FOUND, "family_not_found", "Family not found")
    if err == "wrong_role":
        raise_api_error(status.HTTP_403_FORBIDDEN, "wrong_role", "Only student members may access this endpoint")

    return QuestionsResponse(
        version="starter-1",
        sections=get_public_sections(),
    )


@router.get("/progress", response_model=ProgressResponse)
def get_assessment_progress(
    family_code: str,
    x_member_token: Optional[str] = Header(None, alias="X-Member-Token"),
) -> ProgressResponse:
    err, family, member = family_store.authenticate_student(family_code, x_member_token)
    if err == "invalid_token":
        raise_api_error(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Invalid member token")
    if err == "family_not_found":
        raise_api_error(status.HTTP_404_NOT_FOUND, "family_not_found", "Family not found")
    if err == "wrong_role":
        raise_api_error(status.HTTP_403_FORBIDDEN, "wrong_role", "Only student members may access this endpoint")

    assert member is not None
    return ProgressResponse(
        answers=member.answers,
        submitted=member.submitted,
    )


@router.put("/answers", response_model=PutAnswersResponse)
def put_assessment_answers(
    family_code: str,
    payload: PutAnswersRequest,
    x_member_token: Optional[str] = Header(None, alias="X-Member-Token"),
) -> PutAnswersResponse:
    # 1. Check order: token, family, role
    err, family, member = family_store.authenticate_student(family_code, x_member_token)
    if err == "invalid_token":
        raise_api_error(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Invalid member token")
    if err == "family_not_found":
        raise_api_error(status.HTTP_404_NOT_FOUND, "family_not_found", "Family not found")
    if err == "wrong_role":
        raise_api_error(status.HTTP_403_FORBIDDEN, "wrong_role", "Only student members may access this endpoint")

    assert member is not None
    # 2. Check already_submitted (409) BEFORE validation (422) per Assumption e
    if member.submitted:
        raise_api_error(status.HTTP_409_CONFLICT, "already_submitted", "Assessment has already been submitted")

    # 3. Validate answers all-or-nothing per Assumption c
    is_valid, updates, validation_err = validate_answers_payload(payload.answers)
    if not is_valid:
        raise_api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            validation_err or "Validation error in assessment answers",
        )

    # 4. Save updates into store
    err, answered, total = family_store.update_student_answers(family_code, x_member_token, updates)
    if err == "already_submitted":
        raise_api_error(status.HTTP_409_CONFLICT, "already_submitted", "Assessment has already been submitted")

    return PutAnswersResponse(
        answered=answered,
        total=total,
    )


@router.post("/submit", response_model=SubmitResponse)
def submit_assessment(
    family_code: str,
    x_member_token: Optional[str] = Header(None, alias="X-Member-Token"),
) -> SubmitResponse:
    # 1. Check order: token, family, role
    err, family, member = family_store.authenticate_student(family_code, x_member_token)
    if err == "invalid_token":
        raise_api_error(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Invalid member token")
    if err == "family_not_found":
        raise_api_error(status.HTTP_404_NOT_FOUND, "family_not_found", "Family not found")
    if err == "wrong_role":
        raise_api_error(status.HTTP_403_FORBIDDEN, "wrong_role", "Only student members may access this endpoint")

    # 2. Submit in store
    submit_err, missing = family_store.submit_student_assessment(family_code, x_member_token)
    if submit_err == "assessment_incomplete":
        raise_api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "assessment_incomplete",
            "Required questions are unanswered",
            missing=missing,
        )

    return SubmitResponse(submitted=True)
