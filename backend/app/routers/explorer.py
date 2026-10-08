from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, status

from engine.conflict.config import DEFAULT_CONFIG as CONFLICT_CONFIG
from engine.parent.models import Route
from engine.public import (
    get_default_routes,
    negotiate,
    per_career_scores,
    unified_roadmap,
)

from app.engine_bridge import build_engine_profiles
from app.schemas.assessment import LocalizedText
from app.schemas.explorer import (
    BlendPoint,
    CareerBlocked,
    ExplorerCareer,
    ExplorerCompromise,
    ExplorerResponse,
    ExplorerSlider,
    Remedy,
    RemedyText,
)
from app.schemas.families import RoleEnum
from app.store.families import FamilyRecord, family_store

router = APIRouter(prefix="/families/{family_code}", tags=["explorer"])

CURRENT_DIR = Path(__file__).resolve().parent
HINDI_NAMES_FILE = CURRENT_DIR.parent / "data" / "career_names_hi.json"

_HINDI_CAREER_NAMES: dict[str, str] = {}
if HINDI_NAMES_FILE.exists():
    try:
        with open(HINDI_NAMES_FILE, "r", encoding="utf-8") as f:
            _HINDI_CAREER_NAMES = json.load(f)
    except Exception:
        _HINDI_CAREER_NAMES = {}

GAP_MAP = {
    "market_demand_signals": "regional_hiring",
}


def raise_api_error(status_code: int, code: str, message: str, **kwargs: Any) -> None:
    detail = {"code": code, "message": message}
    detail.update(kwargs)
    raise HTTPException(status_code=status_code, detail=detail)


def rank_blend_items(items: list[dict[str, Any]]) -> list[tuple[str, float, int]]:
    """Sort items by score descending, then career id ascending (ties), and assign 1..N ranks."""
    sorted_items = sorted(
        items,
        key=lambda x: (-round(float(x["negotiated_score"]), 1), str(x["career_id"])),
    )
    return [
        (item["career_id"], round(float(item["negotiated_score"]), 1), rank)
        for rank, item in enumerate(sorted_items, 1)
    ]


def compute_explorer(family: FamilyRecord) -> ExplorerResponse:
    student_profile, parent_profile = build_engine_profiles(family)

    scores = per_career_scores(student_profile, parent_profile)
    family.best_routes_cache = {s["career_id"]: s.get("best_route_id") for s in scores}
    roadmap = unified_roadmap(student_profile, parent_profile)

    blocked_by_cid = {b.career_id: b for b in roadmap.blocked_careers}

    route_list: list[Route] = get_default_routes()
    route_map = {(r.career_id, r.route_id): r for r in route_list}

    positions = list(range(0, 105, 5))
    blends_by_cid: dict[str, list[BlendPoint]] = defaultdict(list)
    pareto_ids_set: set[str] = set()
    compromise_ids_set: set[str] = set()

    for pos in positions:
        alpha = round(1.0 - pos / 100.0, 4)
        neg_res = negotiate(student_profile, parent_profile, alpha=alpha)
        ranked_entries = rank_blend_items(neg_res["ranked_careers"])
        for cid, score, rank in ranked_entries:
            blends_by_cid[cid].append(BlendPoint(score=score, rank=rank))
        if pos == 50:
            pareto_ids_set = set(neg_res["pareto_optimal_career_ids"])
            compromise_ids_set = set(neg_res["compromise_zone_career_ids"])

    non_blocked_careers: list[ExplorerCareer] = []
    blocked_careers: list[ExplorerCareer] = []
    best_routes_map: dict[str, Optional[str]] = {}

    for s in scores:
        cid = s["career_id"]
        cname_en = s["career_name"]
        cname_hi = _HINDI_CAREER_NAMES.get(cid, cname_en)
        name = LocalizedText(en=cname_en, hi=cname_hi)
        domain = s["domain_id"]
        fit = round(s["student_fit"], 1)
        conflict = round(s["career_conflict"], 1)
        data_gaps = [GAP_MAP.get(g, g) for g in s.get("missing_data_fields", [])]

        if s["is_viable"]:
            viability = round(s["family_viability"], 1)
            raw_m = s.get("market_score")
            market = (
                round(float(raw_m), 1)
                if (not s.get("market_is_default") and raw_m != "NOT FOUND" and raw_m is not None)
                else None
            )

            best_rid = s.get("best_route_id")
            r = route_map.get((cid, best_rid)) if best_rid else None
            years_to_income = r.years_to_first_income if r else None
            best_routes_map[cid] = r.route_id if r else best_rid

            in_compromise = cid in compromise_ids_set
            blend = blends_by_cid.get(cid, [])

            non_blocked_careers.append(
                ExplorerCareer(
                    id=cid,
                    name=name,
                    domain=domain,
                    fit=fit,
                    viability=viability,
                    market=market,
                    years_to_income=years_to_income,
                    conflict=conflict,
                    in_compromise=in_compromise,
                    blend=blend,
                    blocked=None,
                    data_gaps=data_gaps,
                )
            )
        else:
            b = blocked_by_cid.get(cid)
            cause_raw = b.block_cause if b else "other"
            cause = (
                cause_raw
                if cause_raw in ("no_route_data", "cost", "academic", "other")
                else "other"
            )

            gates: list[str] = []
            if b:
                for g in b.failed_gates:
                    if g == "G_fin" and "money" not in gates:
                        gates.append("money")
                    elif g == "G_acad" and "academic" not in gates:
                        gates.append("academic")

            if cause in ("cost", "no_route_data") and "money" not in gates:
                gates.insert(0, "money")
            if cause == "academic" and "academic" not in gates:
                gates.append("academic")

            if "money" in gates or cause in ("cost", "no_route_data"):
                viability = None
            else:
                viability = round(s["family_viability"], 1)

            raw_m = s.get("market_score")
            market = (
                round(float(raw_m), 1)
                if (not s.get("market_is_default") and raw_m != "NOT FOUND" and raw_m is not None)
                else None
            )

            if cause == "no_route_data":
                years_to_income = None
                best_routes_map[cid] = None
            else:
                best_rid = s.get("best_route_id")
                r = route_map.get((cid, best_rid)) if best_rid else None
                if r is None:
                    matching = [rt for rt in route_list if rt.career_id == cid]
                    r = matching[0] if matching else None
                years_to_income = r.years_to_first_income if r else None
                best_routes_map[cid] = r.route_id if r else best_rid

            if cause == "no_route_data":
                remedies = []
            elif b and b.constructive_remedies:
                remedies = [
                    Remedy(
                        id=f"rem_{cid}_{idx}",
                        text=RemedyText(en=text, hi=None),
                    )
                    for idx, text in enumerate(b.constructive_remedies)
                ]
            else:
                remedies = []

            blocked_info = CareerBlocked(
                gates=gates,  # type: ignore[arg-type]
                cause=cause,  # type: ignore[arg-type]
                remedies=remedies,
            )

            blocked_careers.append(
                ExplorerCareer(
                    id=cid,
                    name=name,
                    domain=domain,
                    fit=fit,
                    viability=viability,
                    market=market,
                    years_to_income=years_to_income,
                    conflict=conflict,
                    in_compromise=False,
                    blend=None,
                    blocked=blocked_info,
                    data_gaps=data_gaps,
                )
            )

    sorted_non_blocked = sorted(
        non_blocked_careers,
        key=lambda c: (c.blend[10].rank if c.blend and len(c.blend) > 10 else 999, c.id),
    )
    sorted_blocked = sorted(blocked_careers, key=lambda c: c.id)
    all_careers = sorted_non_blocked + sorted_blocked

    pareto_candidates = [c for c in sorted_non_blocked if c.id in pareto_ids_set]
    frontier = [
        c.id
        for c in sorted(
            pareto_candidates,
            key=lambda c: (c.viability if c.viability is not None else 0.0, c.id),
        )
    ]

    if not sorted_non_blocked:
        compromise = None
    else:
        min_fit = round(CONFLICT_CONFIG.min_student_fit_compromise * 100.0, 1)
        min_viability = round(CONFLICT_CONFIG.min_parent_viability_compromise * 100.0, 1)
        compromise = ExplorerCompromise(min_fit=min_fit, min_viability=min_viability)

    slider = ExplorerSlider(positions=positions, default=50)
    family.best_routes_cache = best_routes_map

    return ExplorerResponse(
        slider=slider,
        careers=all_careers,
        frontier=frontier,
        compromise=compromise,
    )


def get_or_compute_explorer(family: FamilyRecord) -> ExplorerResponse:
    if family.explorer_cache is not None and family.best_routes_cache is not None:
        return ExplorerResponse.model_validate(family.explorer_cache)

    response = compute_explorer(family)
    family.explorer_cache = response.model_dump()
    return response


@router.get("/explorer", response_model=ExplorerResponse)
def get_family_explorer(
    family_code: str,
    x_member_token: Optional[str] = Header(None, alias="X-Member-Token"),
) -> ExplorerResponse:
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
            "explorer_not_ready",
            "Both student and parent must submit before accessing the explorer",
        )

    return get_or_compute_explorer(family)
