"""PRISM Engine - Synthesis & Unified Roadmap Layer (Module F).

Connects:
1. Student Fit (Module A): RIASEC, Aptitude, Skills, Big Five, Academic Gates, SWOT.
2. Parent Machine (Module B): Balance Sheet, Cash Capacity, EMI, RB, DSR, G_fin, F_family.
3. Market Machine (Module E): Regional hiring trends, time-series forecasting, disruption risk, F_market.
4. Conflict Index (Module C): Shared dimension alignment, route conflict, negotiation slider, compromise zone.

Produces a fully grounded, ranked, financially viable career roadmap.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from engine.student_fit.models import Student, Career as StudentCareer, Result as StudentResult
from engine.student_fit.scoring import calculate_student_fit
from engine.parent.models import ParentProfile, Route
from engine.parent.scores import evaluate_parent_portfolio
from engine.parent.config import DEFAULT_CONFIG as PARENT_CONFIG, ParentSolverConfig
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
from engine.career_loader import check_career_data_completeness


class RoadmapItem(BaseModel):
    """A feasible recommended career with full financial, fit, and market roadmap metrics."""

    rank: int
    career_id: str
    career_name: str
    domain: str
    best_route_id: str

    # Component Scores [0, 100] or [0, 1]
    student_fit: float = Field(..., description="Student Fit F_student (0-100)")
    family_viability: float = Field(..., description="Family Viability F_family (0-100)")
    market_score: float = Field(..., description="Job Market Viability F_market (0-100)")
    fit_gap: float = Field(default=0.0, description="Per-career |Fit - Family| gap (0-100) (Fix 2)")

    @property
    def career_conflict(self) -> float:
        """Alias for backward compatibility."""
        return self.fit_gap

    # Composite & Negotiation Scores
    composite_score: float = Field(..., description="Blended score (0-100)")
    negotiated_score: float = Field(..., description="Slider-adjusted score (0-100)")
    is_in_compromise_zone: bool = Field(..., description="Qualifies in family compromise zone")
    is_pareto_optimal: bool = Field(..., description="Non-dominated Pareto solution")

    # Guidance & Attributes
    stretch: bool = Field(default=False, description="Whether career is an aptitude stretch (Fix 3)")
    stretch_reasons: List[str] = Field(default_factory=list, description="Specific aptitude shortfalls if stretch")
    market_tier: str = Field(default="stable", description="Market demand/growth tier (Fix 5)")
    data_confidence: str = Field(default="high", description="Data confidence: high, medium, low (Fix 4)")

    # Financial Roadmap Details
    starting_salary: float = Field(..., description="Expected starting salary Y1 (INR)")
    net_cost: float = Field(..., description="Net educational cost after grants (INR)")
    monthly_emi: float = Field(..., description="Monthly loan repayment EMI (INR)")
    repayment_burden: float = Field(..., description="Household repayment burden (ratio)")
    payback_period_years: float = Field(..., description="Estimated loan payback period in years")

    # Guidance & Pathways
    swot_strengths: List[str] = Field(default_factory=list, description="Top student cognitive strengths")
    swot_weaknesses: List[str] = Field(default_factory=list, description="Top trait shortfalls to bridge")
    entrance_exams: List[str] = Field(default_factory=list, description="Mandatory qualifying entrance exams")
    scholarships: List[str] = Field(default_factory=list, description="Applicable merit/means scholarships")
    explanation: str = Field(..., description="Deterministic plain-language rationale")

    # Additive completeness metadata
    data_complete: bool = Field(default=True, description="True if verified cost, salary, and demand data exist")
    missing_data_fields: List[str] = Field(default_factory=list, description="List of unverified/missing data sources")


class BlockedRoadmapItem(BaseModel):
    """A career route that failed academic or financial gates, with constructive remedies."""

    career_id: str
    career_name: str
    failed_gates: List[str] = Field(..., description="Failed gates (G_fin, G_acad)")
    reasons: List[str] = Field(..., description="Diagnostic reasons why pathway is blocked")
    constructive_remedies: List[str] = Field(
        default_factory=list, description="Actionable ways to make route workable"
    )
    cheaper_alternative_routes: List[str] = Field(
        default_factory=list, description="Cheaper pathways to same career"
    )

    # Additive completeness metadata
    data_complete: bool = Field(default=True, description="True if verified cost, salary, and demand data exist")
    missing_data_fields: List[str] = Field(default_factory=list, description="List of unverified/missing data sources")


class FullRoadmapReport(BaseModel):
    """Unified PRISM career guidance roadmap report for the student and family."""

    student_id: str
    family_conflict_score: float = Field(..., description="Overall family conflict (0-100)")
    is_high_family_conflict: bool
    family_diagnosis_summary: str
    dimension_explanations: Dict[str, str]

    negotiation_alpha: float = Field(..., description="Current slider balance (0=parent, 1=student)")
    ranked_careers: List[RoadmapItem]
    compromise_zone_careers: List[RoadmapItem]
    blocked_careers: List[BlockedRoadmapItem]
    recommended_compromise: Optional[RoadmapItem] = None
    balanced_pick: Optional[RoadmapItem] = None
    balanced_pick_career_id: Optional[str] = None


def generate_unified_roadmap(
    student: Student,
    parent: ParentProfile,
    student_careers: List[StudentCareer],
    routes: List[Route],
    market_records: Optional[List[CareerMarketRecord]] = None,
    student_region: Optional[str] = None,
    alpha: float = 0.50,
    parent_config: Optional[ParentSolverConfig] = None,
) -> FullRoadmapReport:
    """Execute the end-to-end PRISM Engine pipeline and synthesize the unified family roadmap.

    Steps:
    1. Student Fit Scoring: F_student, SWOT, G_acad for each career.
    2. Parent Machine Solver: F_family, G_fin, net costs, EMIs for each route.
    3. Market Machine Scoring: F_market for each career from market signals.
    4. Conflict Index Diagnosis: Overall family alignment + per-career conflict gaps.
    5. Negotiation Explorer & Composite Blending: Rank viable options, identify compromise zone.
    """
    # Step 1: Overall Family Conflict Diagnosis
    overall_conflict = compute_overall_conflict(student, parent, CONFLICT_CONFIG)

    # Step 2: Student Fit Scoring per Career
    student_evaluations: Dict[str, StudentResult] = {}
    for sc in student_careers:
        res = calculate_student_fit(student, sc)
        student_evaluations[sc.career_id] = res

    # Step 3: Parent Machine Evaluation across all routes
    parent_eval = evaluate_parent_portfolio(parent, routes, config=parent_config or PARENT_CONFIG)
    # Group viability reports by career_id
    reports_by_career: Dict[str, List[Any]] = {}
    for r in parent_eval.reports:
        reports_by_career.setdefault(r.career_id, []).append(r)

    # Step 4: Market Machine Evaluation per Career
    market_evaluations: Dict[str, MarketReport] = {}
    if market_records:
        cat_result = evaluate_market_catalogue(
            careers=market_records,
            student_region=student_region,
            config=MARKET_CONFIG,
        )
        for rep in cat_result.reports:
            market_evaluations[rep.career_id] = rep

    # Step 5: Evaluate feasible careers vs blocked careers
    feasible_items: List[Dict[str, Any]] = []
    blocked_items: List[BlockedRoadmapItem] = []

    # Map routes by (career_id, route_id)
    routes_dict = {(r.career_id, r.route_id): r for r in routes}

    # Find careers in portfolio
    career_ids = set(student_evaluations.keys()) | {r.career_id for r in routes}

    for cid in career_ids:
        s_eval = student_evaluations.get(cid)
        c_reports = reports_by_career.get(cid, [])
        m_eval = market_evaluations.get(cid)

        c_name = getattr(s_eval, "career_name", cid.replace("_", " ").title())

        # Check Academic Gate
        g_acad_pass = (s_eval.G_acad == 1 and not s_eval.blocked) if s_eval else True

        # Find best financially feasible route
        feasible_routes = [r for r in c_reports if r.g_fin == 1]

        if not g_acad_pass:
            reasons = (
                s_eval.blocked_reasons
                if (s_eval and s_eval.blocked_reasons)
                else ["Academic prerequisites not met (insufficient marks or missing subjects/exams)."]
            )
            is_comp, missing_f = check_career_data_completeness(cid)
            blocked_items.append(
                BlockedRoadmapItem(
                    career_id=cid,
                    career_name=c_name,
                    failed_gates=["G_acad"],
                    reasons=reasons,
                    constructive_remedies=["Focus on qualifying entrance exams or target bridge diploma courses."],
                    data_complete=is_comp,
                    missing_data_fields=missing_f,
                )
            )
            continue

        if not feasible_routes:
            # All routes for this career failed G_fin
            blocked_infos = [b for b in parent_eval.blocked_list if b.career_id == cid]
            reasons = []
            remedies = []
            for b in blocked_infos:
                reasons.extend(b.block_reasons)
                if b.suggestion:
                    remedies.append(b.suggestion)

            if not reasons:
                reasons = ["All available institutional pathways exceed family borrowing capacity or repayment burden."]

            alt_routes = [r.route_id for r in c_reports]
            is_comp, missing_f = check_career_data_completeness(cid)

            blocked_items.append(
                BlockedRoadmapItem(
                    career_id=cid,
                    career_name=c_name,
                    failed_gates=["G_fin"],
                    reasons=list(set(reasons)),
                    constructive_remedies=list(set(remedies)) or ["Apply for state government merit-cum-means fee waivers."],
                    cheaper_alternative_routes=alt_routes,
                    data_complete=is_comp,
                    missing_data_fields=missing_f,
                )
            )
            continue

        # Choose the best feasible route (highest F_family)
        best_route_report = max(feasible_routes, key=lambda x: x.f_family)
        target_route = routes_dict.get((cid, best_route_report.route_id))

        f_student_val = (s_eval.F_student if s_eval else 60.0) / 100.0  # normalized to [0, 1]
        f_family_val = best_route_report.f_family / 100.0  # normalized to [0, 1]
        f_market_val = (m_eval.F_market if m_eval else 70.0) / 100.0  # normalized to [0, 1]

        # Fix 2: Fit gap = |Fit - Family|
        fit_gap_val = round(abs(f_student_val - f_family_val) * 100.0, 1)

        # Fix 1 & 8: Scoring uses two scores (Fit & Family). No conflict penalty!
        comp_score_val = round((0.5 * f_student_val + 0.5 * f_family_val) * 100.0, 1)

        strengths_list = [item.get("trait", str(item)) if isinstance(item, dict) else str(item) for item in s_eval.strengths] if (s_eval and s_eval.strengths) else []
        weaknesses_list = [item.get("trait", str(item)) if isinstance(item, dict) else str(item) for item in s_eval.weaknesses] if (s_eval and s_eval.weaknesses) else []

        # Fix 3: Stretch attributes
        is_stretch = getattr(s_eval, "stretch", False)
        stretch_reasons = getattr(s_eval, "stretch_reasons", [])

        # Fix 4: Data confidence
        data_conf = getattr(best_route_report, "data_confidence", "high")

        # Fix 5: Market tier badge
        m_tier = getattr(m_eval, "velocity_tier", "stable") if m_eval else "stable"

        feasible_items.append({
            "career_id": cid,
            "career_name": c_name,
            "domain": getattr(target_route, "domain", "General"),
            "best_route_id": best_route_report.route_id,
            "student_fit": round(f_student_val * 100.0, 1),
            "family_viability": round(f_family_val * 100.0, 1),
            "market_score": round(f_market_val * 100.0, 1),
            "fit_gap": fit_gap_val,
            "composite_score": comp_score_val,
            "starting_salary": getattr(target_route, "starting_salary", 0.0),
            "net_cost": best_route_report.cost_net,
            "monthly_emi": best_route_report.emi,
            "repayment_burden": round(best_route_report.repayment_burden, 4),
            "payback_period_years": round(best_route_report.payback_years, 1),
            "swot_strengths": strengths_list,
            "swot_weaknesses": weaknesses_list,
            "target_route": target_route,
            "f_student_norm": f_student_val,
            "f_family_norm": f_family_val,
            "f_market_norm": f_market_val,
            "stretch": is_stretch,
            "stretch_reasons": stretch_reasons,
            "market_tier": m_tier,
            "data_confidence": data_conf,
            "status": getattr(best_route_report, "status", "ok"),
        })

    # Step 6: Negotiation Explorer ranking on feasible options
    scored_for_negotiation = [
        ScoredCareerInput(
            career_id=item["career_id"],
            route_id=item["best_route_id"],
            career_name=item["career_name"],
            student_fit=item["f_student_norm"],
            family_viability=item["f_family_norm"],
            market_score=item["f_market_norm"],
            career_risk=getattr(item["target_route"], "career_risk", 0.5),
            domain=item["domain"],
            relocation_need=getattr(item["target_route"], "relocation_need", 0.5),
            years_to_first_income=getattr(item["target_route"], "years_to_first_income", 4.0),
            is_financially_viable=(item["status"] != "insufficient_data"),
            estimated_cost=item["net_cost"],
        )
        for item in feasible_items
    ]

    neg_res = evaluate_negotiation_slider(
        student=student,
        parent=parent,
        careers=scored_for_negotiation,
        alpha=alpha,
        config=CONFLICT_CONFIG,
    )

    # Build final ranked items
    final_ranked: List[RoadmapItem] = []
    for rank_idx, neg_c in enumerate(neg_res.ranked_careers, 1):
        raw = next(item for item in feasible_items if item["career_id"] == neg_c.career_id)

        # Build clear explanation
        exp = (
            f"{raw['career_name']} scored {raw['student_fit']:.0f}% on Student Fit and "
            f"{raw['family_viability']:.0f}% on Family Viability. "
            f"Monthly EMI is INR {raw['monthly_emi']:,.0f} ({raw['repayment_burden']:.1%} of household income). "
            f"{neg_c.summary_reason}"
        )

        is_comp, missing_f = check_career_data_completeness(raw["career_id"])
        final_ranked.append(
            RoadmapItem(
                rank=rank_idx,
                career_id=raw["career_id"],
                career_name=raw["career_name"],
                domain=raw["domain"],
                best_route_id=raw["best_route_id"],
                student_fit=raw["student_fit"],
                family_viability=raw["family_viability"],
                market_score=raw["market_score"],
                fit_gap=raw["fit_gap"],
                composite_score=raw["composite_score"],
                negotiated_score=round(neg_c.negotiated_score * 100.0, 1),
                is_in_compromise_zone=neg_c.is_in_compromise_zone,
                is_pareto_optimal=neg_c.is_pareto_optimal,
                stretch=raw["stretch"],
                stretch_reasons=raw["stretch_reasons"],
                market_tier=raw["market_tier"],
                data_confidence=raw["data_confidence"],
                starting_salary=raw["starting_salary"],
                net_cost=raw["net_cost"],
                monthly_emi=raw["monthly_emi"],
                repayment_burden=raw["repayment_burden"],
                payback_period_years=raw["payback_period_years"],
                swot_strengths=raw["swot_strengths"],
                swot_weaknesses=raw["swot_weaknesses"],
                entrance_exams=[],
                scholarships=[],
                explanation=exp,
                data_complete=is_comp,
                missing_data_fields=missing_f,
            )
        )

    compromise_zone = [item for item in final_ranked if item.is_in_compromise_zone]
    recommended_compromise = compromise_zone[0] if compromise_zone else (final_ranked[0] if final_ranked else None)
    balanced_pick_item = next((item for item in final_ranked if item.career_id == neg_res.balanced_pick_career_id), None)

    return FullRoadmapReport(
        student_id=getattr(student, "student_id", "student_1"),
        family_conflict_score=round(overall_conflict.overall_conflict * 100.0, 1),
        is_high_family_conflict=overall_conflict.is_high_conflict,
        family_diagnosis_summary=overall_conflict.diagnosis_summary,
        dimension_explanations=overall_conflict.dimension_explanations,
        negotiation_alpha=alpha,
        ranked_careers=final_ranked,
        compromise_zone_careers=compromise_zone,
        blocked_careers=blocked_items,
        recommended_compromise=recommended_compromise,
        balanced_pick=balanced_pick_item,
        balanced_pick_career_id=neg_res.balanced_pick_career_id,
    )

