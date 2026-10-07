"""PRISM Engine - Thin Public Facade Layer.

Exposes pure, deterministic functional interfaces for the Udaan backend:
1. overall_conflict: Computes family conflict index (0-100) and 4 stable dimension gaps (0-1).
2. per_career_scores: Evaluates multi-attribute scores and feasibility gates per career.
3. negotiate: Evaluates family negotiation slider balance (alpha) across viable pathways.
4. unified_roadmap: Generates end-to-end full roadmap with Pareto and compromise zone rankings.

Pure functions:
- Zero HTTP endpoints.
- Zero global mutable state.
- Paths are relative to the file.
- Outputs are pure numbers, booleans, and stable snake_case IDs.
- English diagnostic strings are marked as internal/debug only (not for UI display).
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Any, Optional

from engine.student_fit.models import Student, Career as StudentCareer, Result as StudentResult, AcademicRequirement
from engine.student_fit.scoring import calculate_student_fit
from engine.parent.models import ParentProfile, Route
from engine.parent.scores import evaluate_parent_portfolio
from engine.market.models import CareerMarketRecord, MarketReport
from engine.market.scores import evaluate_market_catalogue
from engine.market.config import DEFAULT_CONFIG as MARKET_CONFIG
from engine.conflict.models import ScoredCareerInput
from engine.conflict.scores import (
    compute_overall_conflict,
    compute_career_conflict,
    evaluate_negotiation_slider,
    compute_composite_score,
)
from engine.conflict.config import DEFAULT_CONFIG as CONFLICT_CONFIG
from engine.synthesis import generate_unified_roadmap, FullRoadmapReport, RoadmapItem, BlockedRoadmapItem
from engine.career_loader import (
    load_seed_careers_metadata,
    load_route_costs,
    check_career_data_completeness,
)
from engine.domains import normalize_category_to_domain_id

CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent
DATA_PIPELINE_PROCESSED = WORKSPACE_ROOT / "data_pipeline" / "processed"


# ---------------------------------------------------------------------------
# Default Career & Route Benchmarks Generator (Deterministic Fallbacks)
# ---------------------------------------------------------------------------
_DOMAIN_RIASEC_BENCHMARKS = {
    "tech_engineering": {"R": 0.35, "I": 0.85, "A": 0.30, "S": 0.20, "E": 0.30, "C": 0.70},
    "business_management": {"R": 0.20, "I": 0.40, "A": 0.30, "S": 0.50, "E": 0.85, "C": 0.75},
    "healthcare_medicine": {"R": 0.30, "I": 0.90, "A": 0.20, "S": 0.80, "E": 0.30, "C": 0.60},
    "design_creative": {"R": 0.40, "I": 0.30, "A": 0.90, "S": 0.30, "E": 0.50, "C": 0.40},
    "media_entertainment": {"R": 0.20, "I": 0.30, "A": 0.85, "S": 0.50, "E": 0.80, "C": 0.30},
    "humanities_law": {"R": 0.10, "I": 0.70, "A": 0.60, "S": 0.80, "E": 0.70, "C": 0.60},
    "sciences": {"R": 0.40, "I": 0.95, "A": 0.20, "S": 0.30, "E": 0.20, "C": 0.70},
}


def get_default_student_careers() -> List[StudentCareer]:
    """Build default benchmark StudentCareer objects for all seed careers using relative paths."""
    seed_careers = load_seed_careers_metadata()
    default_careers: List[StudentCareer] = []

    for c in seed_careers:
        cid = c["career_id"]
        cname = c["career_name"]
        dom_id = c["domain_id"]

        riasec = _DOMAIN_RIASEC_BENCHMARKS.get(dom_id, _DOMAIN_RIASEC_BENCHMARKS["tech_engineering"])
        default_careers.append(
            StudentCareer(
                career_id=cid,
                career_name=cname,
                I_c=riasec,
                c_j={"logical": 0.70, "numerical": 0.70, "verbal": 0.60, "spatial": 0.50},
                u_j={"logical": 0.80, "numerical": 0.80, "verbal": 0.70, "spatial": 0.50},
                academic_requirements=AcademicRequirement(
                    min_marks=50.0,
                    required_subjects=[],
                    required_exams=[],
                ),
            )
        )
    return default_careers


def get_default_routes() -> List[Route]:
    """Load default verified routes, with fallback routes if external files are unpopulated."""
    routes = load_route_costs()
    if routes:
        return routes

    # Fallback routes for seed careers
    seed_careers = load_seed_careers_metadata()
    fallback_routes: List[Route] = []
    for c in seed_careers:
        cid = c["career_id"]
        dom_id = c["domain_id"]
        fallback_routes.append(
            Route(
                career_id=cid,
                route_id=f"{cid}_std_route",
                tuition=250000.0,
                living=180000.0,
                exam_equipment=20000.0,
                grant=0.0,
                duration_years=4.0,
                starting_salary=600000.0,
                years_to_first_income=4.0,
                career_risk=0.45,
                relocation_need=0.50,
                domain=dom_id,
                sector="private",
                g_acad=1,
            )
        )
    return fallback_routes


# ---------------------------------------------------------------------------
# 1. Overall Family Conflict Facade
# ---------------------------------------------------------------------------
def overall_conflict(student: Student, parent: ParentProfile) -> Dict[str, Any]:
    """Compute overall parent-student conflict and stable dimension gap metrics.

    Outputs:
    - conflict_index: float in [0.0, 100.0]
    - is_high_conflict: bool
    - dimension_gaps: Dict[str, float] with stable IDs: 'risk', 'domain', 'relocation', 'time' in [0.0, 1.0]
    - dimension_weights: Dict[str, float] with weights (0.25 each)
    - family_diagnosis_summary: str (internal/debug only, not for UI display)
    - dimension_explanations: Dict[str, str] (internal/debug only, not for UI display)
    """
    report = compute_overall_conflict(student, parent, CONFLICT_CONFIG)

    return {
        "conflict_index": round(report.overall_conflict * 100.0, 1),
        "is_high_conflict": report.is_high_conflict,
        "dimension_gaps": {
            "risk": round(report.risk_conflict.gap, 4),
            "domain": round(report.domain_conflict.gap, 4),
            "relocation": round(report.relocation_conflict.gap, 4),
            "time": round(report.time_conflict.gap, 4),
        },
        "dimension_weights": {
            "risk": report.risk_conflict.weight,
            "domain": report.domain_conflict.weight,
            "relocation": report.relocation_conflict.weight,
            "time": report.time_conflict.weight,
        },
        # NOTE: English diagnostic strings are strictly for internal logging/debugging.
        # Frontend/backend should construct display text from dimension IDs.
        "family_diagnosis_summary": report.diagnosis_summary,
        "dimension_explanations": report.dimension_explanations,
    }


# ---------------------------------------------------------------------------
# 2. Per-Career Scoring Facade
# ---------------------------------------------------------------------------
def per_career_scores(
    student: Student,
    parent: ParentProfile,
    careers: Optional[List[StudentCareer]] = None,
    routes: Optional[List[Route]] = None,
    market_records: Optional[List[CareerMarketRecord]] = None,
    student_region: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Compute multi-attribute scores, conflict, and gate eligibility for every career.

    Returns pure list of dicts with numeric scores (0-100), gate flags, and completeness metadata.
    """
    career_list = careers if careers is not None else get_default_student_careers()
    route_list = routes if routes is not None else get_default_routes()

    # 1. Student Fit
    s_evals: Dict[str, StudentResult] = {}
    for sc in career_list:
        s_evals[sc.career_id] = calculate_student_fit(student, sc)

    # 2. Parent Portfolio
    p_eval = evaluate_parent_portfolio(parent, route_list)
    routes_by_career: Dict[str, List[Any]] = {}
    for r in p_eval.reports:
        routes_by_career.setdefault(r.career_id, []).append(r)

    # 3. Market Catalogue
    m_evals: Dict[str, MarketReport] = {}
    if market_records:
        cat_res = evaluate_market_catalogue(market_records, student_region=student_region, config=MARKET_CONFIG)
        for rep in cat_res.reports:
            m_evals[rep.career_id] = rep

    # 4. Map routes
    route_map = {(r.career_id, r.route_id): r for r in route_list}

    all_cids = sorted(list(set(s_evals.keys()) | {r.career_id for r in route_list}))
    results: List[Dict[str, Any]] = []

    for cid in all_cids:
        s_res = s_evals.get(cid)
        c_reports = routes_by_career.get(cid, [])
        feasible_routes = [r for r in c_reports if r.g_fin == 1]

        g_acad = s_res.G_acad if s_res else 1
        g_fin = 1 if feasible_routes else 0
        is_viable = (g_acad == 1) and (g_fin == 1)

        f_student = (s_res.F_student / 100.0) if s_res else 0.5
        best_r = max(feasible_routes, key=lambda x: x.f_family) if feasible_routes else (c_reports[0] if c_reports else None)
        f_family = (best_r.f_family / 100.0) if best_r else 0.0

        m_rep = m_evals.get(cid)
        f_market = (m_rep.market_score / 100.0) if m_rep else 0.5

        # Career conflict
        target_route = route_map.get((cid, best_r.route_id)) if best_r else None
        if target_route:
            c_conf_rep = compute_career_conflict(student, parent, target_route, CONFLICT_CONFIG)
            c_conflict = c_conf_rep.career_conflict
        else:
            c_conflict = 0.5

        # Composite score
        comp = compute_composite_score(f_student, f_family, f_market, c_conflict, CONFLICT_CONFIG)

        is_complete, missing_fields = check_career_data_completeness(cid)

        # Career name and domain
        c_name = s_res.career_name if s_res else (target_route.career_id if target_route else cid)
        domain_id = target_route.domain if target_route else "tech_engineering"

        results.append({
            "career_id": cid,
            "career_name": c_name,
            "domain_id": normalize_category_to_domain_id(domain_id),
            "student_fit": round(f_student * 100.0, 1),
            "family_viability": round(f_family * 100.0, 1),
            "market_score": round(f_market * 100.0, 1),
            "career_conflict": round(c_conflict * 100.0, 1),
            "composite_score": round(comp * 100.0, 1),
            "g_acad": g_acad,
            "g_fin": g_fin,
            "is_viable": is_viable,
            "data_complete": is_complete,
            "missing_data_fields": missing_fields,
        })

    return results


# ---------------------------------------------------------------------------
# 3. Negotiation Explorer Facade
# ---------------------------------------------------------------------------
def negotiate(
    student: Student,
    parent: ParentProfile,
    alpha: float,
    careers: Optional[List[StudentCareer]] = None,
    routes: Optional[List[Route]] = None,
    market_records: Optional[List[CareerMarketRecord]] = None,
    student_region: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate family negotiation balance slider at position alpha in [0.0, 1.0].

    Returns ranked viable careers, compromise zone career IDs, and Pareto optimal IDs.
    """
    alpha = max(0.0, min(1.0, float(alpha)))

    scores = per_career_scores(
        student=student,
        parent=parent,
        careers=careers,
        routes=routes,
        market_records=market_records,
        student_region=student_region,
    )

    # Filter strictly to viable pathways
    viable = [s for s in scores if s["is_viable"]]

    # Build ScoredCareerInput objects for the negotiation solver
    route_list = routes if routes is not None else get_default_routes()
    route_map = {(r.career_id, r.route_id): r for r in route_list}

    scored_inputs = []
    for s in viable:
        cid = s["career_id"]
        # Find first matching route
        matching_routes = [r for r in route_list if r.career_id == cid]
        r_inst = matching_routes[0] if matching_routes else None

        scored_inputs.append(
            ScoredCareerInput(
                career_id=cid,
                route_id=r_inst.route_id if r_inst else f"{cid}_route",
                career_name=s["career_name"],
                student_fit=s["student_fit"] / 100.0,
                family_viability=s["family_viability"] / 100.0,
                market_score=s["market_score"] / 100.0,
                career_risk=getattr(r_inst, "career_risk", 0.5),
                domain=s["domain_id"],
                relocation_need=getattr(r_inst, "relocation_need", 0.5),
                years_to_first_income=getattr(r_inst, "years_to_first_income", 4.0),
                is_financially_viable=True,
                estimated_cost=getattr(r_inst, "tuition", 250000.0),
            )
        )

    neg_res = evaluate_negotiation_slider(
        student=student,
        parent=parent,
        careers=scored_inputs,
        alpha=alpha,
        config=CONFLICT_CONFIG,
    )

    ranked_items = [
        {
            "rank": idx,
            "career_id": c.career_id,
            "negotiated_score": round(c.negotiated_score * 100.0, 1),
            "student_fit": round(c.student_fit * 100.0, 1),
            "family_viability": round(c.family_viability * 100.0, 1),
            "is_in_compromise_zone": c.is_in_compromise_zone,
            "is_pareto_optimal": c.is_pareto_optimal,
        }
        for idx, c in enumerate(neg_res.ranked_careers, 1)
    ]

    compromise_ids = [c["career_id"] for c in ranked_items if c["is_in_compromise_zone"]]
    pareto_ids = [c["career_id"] for c in ranked_items if c["is_pareto_optimal"]]
    recommended_id = compromise_ids[0] if compromise_ids else (ranked_items[0]["career_id"] if ranked_items else None)

    return {
        "alpha": alpha,
        "ranked_careers": ranked_items,
        "compromise_zone_career_ids": compromise_ids,
        "pareto_optimal_career_ids": pareto_ids,
        "recommended_career_id": recommended_id,
    }


# ---------------------------------------------------------------------------
# 4. Unified Full Roadmap Facade
# ---------------------------------------------------------------------------
def unified_roadmap(
    student: Student,
    parent: ParentProfile,
    alpha: float = 0.50,
    careers: Optional[List[StudentCareer]] = None,
    routes: Optional[List[Route]] = None,
    market_records: Optional[List[CareerMarketRecord]] = None,
    student_region: Optional[str] = None,
) -> FullRoadmapReport:
    """Execute the end-to-end PRISM Engine and synthesize the full unified family roadmap.

    Pure facade delegating to generate_unified_roadmap with relative fallback defaults.
    """
    career_list = careers if careers is not None else get_default_student_careers()
    route_list = routes if routes is not None else get_default_routes()

    return generate_unified_roadmap(
        student=student,
        parent=parent,
        student_careers=career_list,
        routes=route_list,
        market_records=market_records,
        student_region=student_region,
        alpha=alpha,
    )
