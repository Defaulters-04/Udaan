from typing import Any, Optional
from fastapi import APIRouter, Header, HTTPException, status

from engine.domains import CANONICAL_DOMAINS
from engine.public import overall_conflict

from app.engine_bridge import build_engine_profiles
from app.schemas.families import RoleEnum
from app.schemas.mirror import (
    MirrorResponse,
    PicksDimension,
    ScaleDimension,
)
from app.shared_questions import (
    MIRROR_DOMAIN_OPTIONS,
    RELOCATION_OPTIONS,
    RELOCATION_STEPS,
    RISK_STEPS,
    TIME_TO_EARN_OPTIONS,
    TIME_TO_EARN_STEPS,
)
from app.store.families import family_store

router = APIRouter(prefix="/families/{family_code}", tags=["mirror"])


def raise_api_error(status_code: int, code: str, message: str, **kwargs: Any) -> None:
    detail = {"code": code, "message": message}
    detail.update(kwargs)
    raise HTTPException(status_code=status_code, detail=detail)


@router.get("/mirror", response_model=MirrorResponse)
def get_family_mirror(
    family_code: str,
    x_member_token: Optional[str] = Header(None, alias="X-Member-Token"),
) -> MirrorResponse:
    err, family, member = family_store.authenticate_member(family_code, x_member_token)
    if err == "invalid_token":
        raise_api_error(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Invalid member token")
    if err == "family_not_found":
        raise_api_error(status.HTTP_404_NOT_FOUND, "family_not_found", "Family not found")

    assert family is not None

    student_member = family.get_member_by_role(RoleEnum.STUDENT)
    parent_member = family.get_member_by_role(RoleEnum.PARENT)

    if (
        student_member is None
        or not student_member.submitted
        or parent_member is None
        or not parent_member.intake_submitted
    ):
        raise_api_error(
            status.HTTP_409_CONFLICT,
            "mirror_not_ready",
            "Both student and parent must submit before accessing the mirror",
        )

    s_answers = student_member.answers or {}
    p_answers = parent_member.intake_answers or {}

    # Call engine through pure bridge
    student_profile, parent_profile = build_engine_profiles(family)
    conflict_res = overall_conflict(student_profile, parent_profile)

    conflict_index = conflict_res["conflict_index"]
    dimension_gaps = conflict_res["dimension_gaps"]
    dimension_weights = conflict_res["dimension_weights"]

    # 1. Risk scale dimension
    student_risk_step = sum(
        1 for q in ("pref_risk_1", "pref_risk_2", "pref_risk_3")
        if s_answers.get(q) == "gamble"
    )
    parent_risk_step = sum(
        1 for q in ("risk_1", "risk_2", "risk_3")
        if p_answers.get(q) == "gamble"
    )

    # 2. Domain picks dimension
    canonical_ids = [d.id for d in CANONICAL_DOMAINS]

    s_wishes = s_answers.get("pref_domain_wish")
    s_wishes_set = set(s_wishes) if isinstance(s_wishes, (list, tuple, set)) else ({s_wishes} if s_wishes else set())
    student_picks = [cid for cid in canonical_ids if cid in s_wishes_set]

    p_wishes = p_answers.get("domain_wish")
    p_wishes_set = set(p_wishes) if isinstance(p_wishes, (list, tuple, set)) else ({p_wishes} if p_wishes else set())
    parent_picks = [cid for cid in canonical_ids if cid in p_wishes_set]

    raw_guess = p_answers.get("guess_domain")
    parent_guess = raw_guess if (raw_guess and raw_guess != "not_sure" and raw_guess in canonical_ids) else None

    # 3. Relocation scale dimension
    reloc_indices = {opt.id: idx for idx, opt in enumerate(RELOCATION_OPTIONS)}
    student_reloc_step = reloc_indices.get(s_answers.get("pref_relocation"), 0)
    parent_reloc_step = reloc_indices.get(p_answers.get("relocation"), 0)

    # 4. Time scale dimension
    time_indices = {opt.id: idx for idx, opt in enumerate(TIME_TO_EARN_OPTIONS)}
    student_time_step = time_indices.get(s_answers.get("pref_time_to_earn"), 0)
    parent_time_step = time_indices.get(p_answers.get("time_to_earn"), 0)

    # Strict dimension order: risk, domain, relocation, time
    dimensions = [
        ScaleDimension(
            id="risk",
            gap=dimension_gaps["risk"],
            weight=dimension_weights["risk"],
            kind="scale",
            steps=RISK_STEPS,
            student_step=student_risk_step,
            parent_step=parent_risk_step,
        ),
        PicksDimension(
            id="domain",
            gap=dimension_gaps["domain"],
            weight=dimension_weights["domain"],
            kind="picks",
            options=MIRROR_DOMAIN_OPTIONS,
            student_picks=student_picks,
            parent_picks=parent_picks,
            parent_guess=parent_guess,
        ),
        ScaleDimension(
            id="relocation",
            gap=dimension_gaps["relocation"],
            weight=dimension_weights["relocation"],
            kind="scale",
            steps=RELOCATION_STEPS,
            student_step=student_reloc_step,
            parent_step=parent_reloc_step,
        ),
        ScaleDimension(
            id="time",
            gap=dimension_gaps["time"],
            weight=dimension_weights["time"],
            kind="scale",
            steps=TIME_TO_EARN_STEPS,
            student_step=student_time_step,
            parent_step=parent_time_step,
        ),
    ]

    return MirrorResponse(
        conflict_index=conflict_index,
        dimensions=dimensions,
    )
