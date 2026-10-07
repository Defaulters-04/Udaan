from typing import Optional
from fastapi import APIRouter, Header, HTTPException, status

from app.schemas.families import (
    CreateFamilyRequest,
    CreateFamilyResponse,
    FamilyPreviewResponse,
    FamilyStatusResponse,
    JoinFamilyRequest,
    JoinFamilyResponse,
    MemberSummary,
    RoleEnum,
    StatusMemberSummary,
)
from app.store.families import family_store, format_iso8601

router = APIRouter(prefix="/families", tags=["families"])


def raise_api_error(status_code: int, code: str, message: str) -> None:
    raise HTTPException(status_code=status_code, detail={"code": code, "message": message})


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreateFamilyResponse)
def create_family(payload: CreateFamilyRequest) -> CreateFamilyResponse:
    family, member = family_store.create_family(
        role=payload.role,
        name=payload.name,
        lang=payload.lang,
    )
    return CreateFamilyResponse(
        family_code=family.family_code,
        member_token=member.token,
        role=member.role.value,
        expires_at=format_iso8601(family.expires_at),
    )


@router.get("/{family_code}/preview", response_model=FamilyPreviewResponse)
def get_family_preview(family_code: str) -> FamilyPreviewResponse:
    family = family_store.get_family_for_preview(family_code)
    if family is None:
        raise_api_error(status.HTTP_404_NOT_FOUND, "family_not_found", "Family not found")

    return FamilyPreviewResponse(
        family_code=family.family_code,
        open_role=family.open_role,
        creator_name=family.creator.name,
    )


@router.post("/{family_code}/join", response_model=JoinFamilyResponse)
def join_family(family_code: str, payload: JoinFamilyRequest) -> JoinFamilyResponse:
    err, family, new_member, partner = family_store.join_family(
        raw_code=family_code,
        role=payload.role,
        name=payload.name,
        lang=payload.lang,
    )
    if err == "family_not_found":
        raise_api_error(status.HTTP_404_NOT_FOUND, "family_not_found", "Family not found")
    if err == "role_taken":
        raise_api_error(status.HTTP_409_CONFLICT, "role_taken", "That role is already taken in this family")
    if err == "family_full":
        raise_api_error(status.HTTP_409_CONFLICT, "family_full", "Family already has both members")

    assert family is not None and new_member is not None and partner is not None
    return JoinFamilyResponse(
        family_code=family.family_code,
        member_token=new_member.token,
        role=new_member.role.value,
        partner=MemberSummary(role=partner.role.value, name=partner.name),
        expires_at=format_iso8601(family.expires_at),
    )


@router.get("/{family_code}/status", response_model=FamilyStatusResponse)
def get_family_status(
    family_code: str,
    x_member_token: Optional[str] = Header(None, alias="X-Member-Token"),
) -> FamilyStatusResponse:
    if not x_member_token:
        raise_api_error(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Invalid member token")

    err, family, you, partner = family_store.get_family_status(
        raw_code=family_code,
        token=x_member_token,
    )
    if err == "family_not_found":
        raise_api_error(status.HTTP_404_NOT_FOUND, "family_not_found", "Family not found")
    if err == "invalid_token":
        raise_api_error(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Invalid member token")

    assert family is not None and you is not None
    if you.role == RoleEnum.STUDENT:
        you_done = you.submitted
        partner_done = partner.intake_submitted if partner else False
    else:
        you_done = you.intake_submitted
        partner_done = partner.submitted if partner else False

    return FamilyStatusResponse(
        family_code=family.family_code,
        linked=partner is not None,
        you=StatusMemberSummary(role=you.role.value, name=you.name, done=you_done),
        partner=StatusMemberSummary(role=partner.role.value, name=partner.name, done=partner_done) if partner else None,
        expires_at=format_iso8601(family.expires_at),
    )
