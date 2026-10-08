from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, status

from engine.career_loader import load_seed_careers_metadata
from engine.parent.scores import evaluate_parent_portfolio
from engine.public import (
    get_default_routes,
    get_default_student_careers,
)
from engine.student_fit.scoring import calculate_student_fit

from app.engine_bridge import build_engine_profiles
from app.routers.explorer import get_or_compute_explorer
from app.schemas.career import (
    CareerDetailResponse,
    DemandInfo,
    EntrySalary,
    FamilyMoney,
    GrowthAreaItem,
    RouteCostParts,
    RouteItem,
)
from app.schemas.explorer import RemedyText
from app.schemas.families import RoleEnum
from app.store.families import family_store

router = APIRouter(prefix="/families/{family_code}", tags=["career"])

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DATA_PIPELINE_PROCESSED = WORKSPACE_ROOT / "data_pipeline" / "processed"


def raise_api_error(status_code: int, code: str, message: str, **kwargs: Any) -> None:
    detail = {"code": code, "message": message}
    detail.update(kwargs)
    raise HTTPException(status_code=status_code, detail=detail)


# ---------------------------------------------------------------------------
# In-memory cached dataset loaders
# ---------------------------------------------------------------------------
_ALL_KNOWN_CAREER_IDS: Optional[set[str]] = None
_ROUTES_DATA: Optional[dict[str, list[dict[str, Any]]]] = None
_ENTRY_SALARIES_DATA: Optional[dict[str, dict[str, Any]]] = None
_DEMANDS_DATA: Optional[dict[str, dict[str, str]]] = None
_EXAMS_DATA: Optional[dict[str, list[str]]] = None


def get_all_known_career_ids() -> set[str]:
    global _ALL_KNOWN_CAREER_IDS
    if _ALL_KNOWN_CAREER_IDS is None:
        _ALL_KNOWN_CAREER_IDS = {c["career_id"] for c in load_seed_careers_metadata()}
    return _ALL_KNOWN_CAREER_IDS


def get_routes_data() -> dict[str, list[dict[str, Any]]]:
    global _ROUTES_DATA
    if _ROUTES_DATA is not None:
        return _ROUTES_DATA

    routes_by_career: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rc_file = DATA_PIPELINE_PROCESSED / "route_costs.csv"
    if rc_file.exists():
        try:
            with open(rc_file, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    cid = row.get("career_id", "").strip()
                    rid = row.get("route_id", "").strip()
                    if not cid or not rid:
                        continue

                    inst = row.get("institution_name", "").strip()
                    prog = row.get("program_name", "").strip()
                    if inst and prog:
                        label = f"{inst} ({prog})"
                    else:
                        label = inst or prog or rid

                    dur = row.get("duration_years")
                    years = float(dur) if dur not in ("NOT FOUND", "", None) else None

                    tot = row.get("total_route_cost")
                    total_cost = float(tot) if tot not in ("NOT FOUND", "", None) else None

                    tui = row.get("tuition_fee_total")
                    tuition = float(tui) if tui not in ("NOT FOUND", "", None) else None

                    hos = row.get("hostel_fee_total")
                    mes = row.get("mess_fee_total")
                    hostel = float(hos) if hos not in ("NOT FOUND", "", None) else None
                    mess = float(mes) if mes not in ("NOT FOUND", "", None) else None
                    if hostel is not None and mess is not None:
                        living = hostel + mess
                    elif hostel is not None:
                        living = hostel
                    elif mess is not None:
                        living = mess
                    else:
                        living = None

                    ent = row.get("entrance_fee")
                    entrance = float(ent) if ent not in ("NOT FOUND", "", None) else None

                    cost_status = row.get("cost_status", "unverified").strip() or "unverified"

                    routes_by_career[cid].append({
                        "id": rid,
                        "label": label,
                        "years": years,
                        "total_cost": total_cost,
                        "tuition": tuition,
                        "living": living,
                        "entrance": entrance,
                        "cost_status": cost_status,
                    })
        except Exception:
            pass

    _ROUTES_DATA = routes_by_career
    return _ROUTES_DATA


def get_entry_salaries_data() -> dict[str, dict[str, Any]]:
    global _ENTRY_SALARIES_DATA
    if _ENTRY_SALARIES_DATA is not None:
        return _ENTRY_SALARIES_DATA

    salaries: dict[str, dict[str, Any]] = {}
    sb_file = DATA_PIPELINE_PROCESSED / "salary_bands.csv"
    if sb_file.exists():
        try:
            with open(sb_file, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("level") != "entry_level_0_to_2_yr":
                        continue
                    cid = row.get("career_id", "").strip()
                    if not cid or cid in salaries:
                        continue

                    p10 = row.get("p10")
                    p50 = row.get("p50")
                    p90 = row.get("p90")
                    src = row.get("source_name", "").strip()

                    min_val = round(float(p10) * 100000.0, 2) if (p10 and p10 != "NOT FOUND") else None
                    med_val = round(float(p50) * 100000.0, 2) if (p50 and p50 != "NOT FOUND") else None
                    max_val = round(float(p90) * 100000.0, 2) if (p90 and p90 != "NOT FOUND") else None

                    if src or any(v is not None for v in (min_val, med_val, max_val)):
                        salaries[cid] = {
                            "min": min_val,
                            "median": med_val,
                            "max": max_val,
                            "unit": "inr_per_year",
                            "source": src or "Official Data",
                        }
        except Exception:
            pass

    _ENTRY_SALARIES_DATA = salaries
    return _ENTRY_SALARIES_DATA


def get_demands_data() -> dict[str, dict[str, str]]:
    global _DEMANDS_DATA
    if _DEMANDS_DATA is not None:
        return _DEMANDS_DATA

    sources: dict[str, str] = {}
    ms_file = DATA_PIPELINE_PROCESSED / "market_signals.csv"
    if ms_file.exists():
        try:
            with open(ms_file, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    cid = row.get("career_id", "").strip()
                    src = row.get("source_name", "").strip()
                    if cid and src and cid not in sources:
                        sources[cid] = src
        except Exception:
            pass

    demands: dict[str, dict[str, str]] = {}
    dc_file = DATA_PIPELINE_PROCESSED / "demand_coverage.csv"
    if dc_file.exists():
        try:
            with open(dc_file, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    cid = row.get("career_id", "").strip()
                    direction = row.get("demand_direction", "").strip()
                    if not cid or not direction or direction == "INSUFFICIENT_EVIDENCE":
                        continue
                    if direction == "GROWING":
                        sig = "positive"
                    elif direction in ("STABLE", "STABLE / MIXED"):
                        sig = "neutral"
                    elif direction == "DECLINING":
                        sig = "negative"
                    else:
                        sig = None
                    if sig:
                        demands[cid] = {
                            "signal": sig,
                            "source": sources.get(cid, "Market Demand Signals"),
                        }
        except Exception:
            pass

    _DEMANDS_DATA = demands
    return _DEMANDS_DATA


def get_exams_data() -> dict[str, list[str]]:
    global _EXAMS_DATA
    if _EXAMS_DATA is not None:
        return _EXAMS_DATA

    exams_map: dict[str, list[str]] = defaultdict(list)
    hss_file = DATA_PIPELINE_PROCESSED / "hss_career_profiles.json"
    if hss_file.exists():
        try:
            with open(hss_file, "r", encoding="utf-8") as f:
                profiles = json.load(f)
                for p in profiles:
                    cid = p.get("career_id")
                    exs = p.get("entrance_exams_pathways", [])
                    if cid and exs:
                        exams_map[cid].extend(exs)
        except Exception:
            pass

    cutoffs_file = DATA_PIPELINE_PROCESSED / "cutoffs.csv"
    if cutoffs_file.exists():
        try:
            with open(cutoffs_file, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    exam = row.get("exam", "").strip()
                    prog = row.get("programme", "").lower()
                    if not exam:
                        continue
                    if "computer" in prog or "data science" in prog or "artificial intelligence" in prog:
                        for c in ("software_developer", "ai_ml_engineer", "data_scientist"):
                            if exam not in exams_map[c]:
                                exams_map[c].append(exam)
                    elif "civil" in prog:
                        if exam not in exams_map["civil_engineer"]:
                            exams_map["civil_engineer"].append(exam)
                    elif "mechanical" in prog:
                        if exam not in exams_map["mechanical_engineer"]:
                            exams_map["mechanical_engineer"].append(exam)
                    elif "electrical" in prog:
                        if exam not in exams_map["electrical_engineer"]:
                            exams_map["electrical_engineer"].append(exam)
                    elif "chemical" in prog:
                        if exam not in exams_map["chemical_engineer"]:
                            exams_map["chemical_engineer"].append(exam)
                    elif "aerospace" in prog:
                        if exam not in exams_map["aerospace_engineer"]:
                            exams_map["aerospace_engineer"].append(exam)
                    elif "mbbs" in prog:
                        if exam not in exams_map["doctor_mbbs"]:
                            exams_map["doctor_mbbs"].append(exam)
        except Exception:
            pass

    _EXAMS_DATA = dict(exams_map)
    return _EXAMS_DATA


# ---------------------------------------------------------------------------
# Career Detail Endpoint
# ---------------------------------------------------------------------------
@router.get("/careers/{career_id}", response_model=CareerDetailResponse)
def get_career_detail(
    family_code: str,
    career_id: str,
    x_member_token: Optional[str] = Header(None, alias="X-Member-Token"),
) -> CareerDetailResponse:
    # 1. Token validation
    if not x_member_token or not x_member_token.strip():
        raise_api_error(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Invalid member token")

    # 2. Family & 3. Membership validation
    err, family, member = family_store.authenticate_member(family_code, x_member_token)
    if err == "family_not_found":
        raise_api_error(status.HTTP_404_NOT_FOUND, "family_not_found", "Family not found")
    if err == "invalid_token":
        raise_api_error(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Invalid member token")

    assert family is not None
    assert member is not None

    # 4. Career ID validation (check against known catalog before readiness)
    known_career_ids = get_all_known_career_ids()
    if career_id not in known_career_ids:
        raise_api_error(status.HTTP_404_NOT_FOUND, "career_not_found", "Career not found")

    # 5. Readiness check (both student and parent must submit)
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
            "Both student and parent must submit before accessing career details",
        )

    # Step 2: Shared Explorer computation reuse
    explorer_res = get_or_compute_explorer(family)
    target_career = next((c for c in explorer_res.careers if c.id == career_id), None)
    if target_career is None:
        raise_api_error(status.HTTP_404_NOT_FOUND, "career_not_found", "Career not found")

    student_profile, parent_profile = build_engine_profiles(family)
    best_route_id = family.best_routes_cache.get(career_id) if family.best_routes_cache else None

    # Step 3: Routes arrangement (up to 5, best first)
    raw_routes_map = get_routes_data()
    raw_routes = raw_routes_map.get(career_id, [])

    if target_career.blocked and target_career.blocked.cause == "no_route_data":
        routes: list[RouteItem] = []
    elif not raw_routes:
        routes = []
    else:
        built_routes: list[RouteItem] = []
        for r in raw_routes:
            is_best = (r["id"] == best_route_id)
            built_routes.append(
                RouteItem(
                    id=r["id"],
                    label=r["label"],
                    years=r["years"],
                    total_cost=r["total_cost"],
                    cost_parts=RouteCostParts(
                        tuition=r["tuition"],
                        living=r["living"],
                        entrance=r["entrance"],
                    ),
                    cost_status=r["cost_status"],
                    is_best=is_best,
                )
            )
        # Order best first, then up to 5 routes total
        routes = sorted(built_routes, key=lambda r: 0 if r.is_best else 1)[:5]

    # Entry salary
    salaries_map = get_entry_salaries_data()
    sal_info = salaries_map.get(career_id)
    if sal_info is not None:
        entry_salary: Optional[EntrySalary] = EntrySalary(
            min=sal_info["min"],
            median=sal_info["median"],
            max=sal_info["max"],
            unit="inr_per_year",
            source=sal_info["source"],
        )
    else:
        entry_salary = None

    # Demand
    demands_map = get_demands_data()
    d_info = demands_map.get(career_id)
    if d_info is not None:
        demand: Optional[DemandInfo] = DemandInfo(
            signal=d_info["signal"],  # type: ignore[arg-type]
            source=d_info["source"],
        )
    else:
        demand = None

    # Exams
    exams_map = get_exams_data()
    exams = exams_map.get(career_id, [])

    # Scholarships (no external database exists)
    scholarships = None

    # Step 4: Role-specific fields
    growth_areas: Optional[list[GrowthAreaItem]] = None
    family_money: Optional[FamilyMoney] = None

    if member.role == RoleEnum.STUDENT:
        # Student view: growth_areas populated, family_money is None
        student_careers = get_default_student_careers()
        sc = next((c for c in student_careers if c.career_id == career_id), None)
        if sc is not None:
            s_res = calculate_student_fit(student_profile, sc)
            if s_res.weaknesses:
                growth_areas = [
                    GrowthAreaItem(
                        id=f"gap_{w['trait']}",
                        text=RemedyText(
                            en=f"{w['trait']}: shortfall of {w['shortfall']:.2f} (required {w['required_level']:.2f}, student {w['student_level']:.2f})",
                            hi=None,
                        ),
                    )
                    for w in s_res.weaknesses
                ]
            else:
                growth_areas = []
        else:
            growth_areas = []
        family_money = None

    elif member.role == RoleEnum.PARENT:
        # Parent view: family_money populated for best route, growth_areas is None
        growth_areas = None
        if target_career.blocked and target_career.blocked.cause == "no_route_data":
            family_money = None
        elif best_route_id:
            default_routes = get_default_routes()
            parent_eval = evaluate_parent_portfolio(parent_profile, default_routes)
            best_rep = next(
                (r for r in parent_eval.reports if r.career_id == career_id and r.route_id == best_route_id),
                None,
            )
            if best_rep is not None:
                family_money = FamilyMoney(
                    loan_need=round(best_rep.loan_needed, 2),
                    monthly_emi=round(best_rep.emi, 2),
                )
            else:
                family_money = None
        else:
            family_money = None

    return CareerDetailResponse(
        id=target_career.id,
        name=target_career.name,
        domain=target_career.domain,
        fit=target_career.fit,
        viability=target_career.viability,
        market=target_career.market,
        years_to_income=target_career.years_to_income,
        conflict=target_career.conflict,
        in_compromise=target_career.in_compromise,
        blocked=target_career.blocked,
        routes=routes,
        entry_salary=entry_salary,
        demand=demand,
        exams=exams,
        scholarships=scholarships,
        growth_areas=growth_areas,
        family_money=family_money,
        data_gaps=target_career.data_gaps,
    )
