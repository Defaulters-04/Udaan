"""Core scoring functions for the PRISM Conflict Index.

Two modes:
1. Overall family diagnosis — student vector vs parent vector on the four shared
   dimensions (risk appetite, domain preference, relocation willingness, time-to-earn).
2. Per-career — how much student and parent disagree about a specific career route.
   For a route, we compare each side's *fit* with the route and take the gap between
   the two fits; the weighted sum of per-dimension fit-gaps is the career conflict.
3. Negotiation slider & compromise zone — finds careers both sides can live with,
   ranked by negotiation balance alpha in [0, 1].
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
import math

from .config import ConflictConfig, DEFAULT_CONFIG
from .models import (
    DimensionConflict,
    OverallConflictReport,
    CareerConflictReport,
    ConflictEvaluation,
    CompromiseCareer,
    NegotiationResponse,
    _clamp,
)


# Domain rating scales: student.domain_preference and parent.domain_ratings both
# use a 1-5 rating scale.
DOMAIN_RATING_SCALE_MIN = 1.0
DOMAIN_RATING_SCALE_MAX = 5.0


def _domain_conflict(student_pref: Dict[str, float], parent_pref: Dict[str, float]) -> DimensionConflict:
    """Compute domain preference conflict.

    Overlap only the domains BOTH sides rated (union of keys, missing = neutral 3).
    For a domain rated by only one side, use neutral (3) for the other so the gap
    reflects genuine divergence, not incomplete data.
    """
    domains = set(student_pref.keys()) | set(parent_pref.keys())
    if not domains:
        return DimensionConflict(
            dimension="domain",
            student_value=3.0,
            parent_value=3.0,
            gap=0.0,
            weight=DEFAULT_CONFIG.w_domain,
        )

    total_gap = 0.0
    for d in domains:
        s = float(student_pref.get(d, 3.0))
        p = float(parent_pref.get(d, 3.0))
        total_gap += abs(s - p) / (DOMAIN_RATING_SCALE_MAX - DOMAIN_RATING_SCALE_MIN)

    return DimensionConflict(
        dimension="domain",
        student_value=float(sum(student_pref.values()) / len(student_pref)) if student_pref else 3.0,
        parent_value=float(sum(parent_pref.values()) / len(parent_pref)) if parent_pref else 3.0,
        gap=_clamp(total_gap / len(domains)),
        weight=DEFAULT_CONFIG.w_domain,
    )


def _risk_conflict(student_risk: float, parent_risk: float) -> DimensionConflict:
    """Compute risk appetite conflict on a 0-1 scale."""
    return DimensionConflict(
        dimension="risk",
        student_value=_clamp(student_risk),
        parent_value=_clamp(parent_risk),
        gap=_clamp(abs(student_risk - parent_risk)),
        weight=DEFAULT_CONFIG.w_risk,
    )


def _relocation_conflict(student_rel: float, parent_rel: float) -> DimensionConflict:
    """Compute relocation willingness conflict on a 0-1 scale."""
    return DimensionConflict(
        dimension="relocation",
        student_value=_clamp(student_rel),
        parent_value=_clamp(parent_rel),
        gap=_clamp(abs(student_rel - parent_rel)),
        weight=DEFAULT_CONFIG.w_relocation,
    )


def _time_conflict(student_years: float, parent_years: float) -> DimensionConflict:
    """Compute time-to-earn conflict.

    Normalized by the larger of the two horizons so a 2-year difference between
    2-year and 4-year targets (100% gap) is scored larger than the same 2-year
    difference between 8-year and 10-year targets (20% gap).
    """
    denom = max(student_years, parent_years, 1.0)
    return DimensionConflict(
        dimension="time",
        student_value=student_years,
        parent_value=parent_years,
        gap=_clamp(abs(student_years - parent_years) / denom),
        weight=DEFAULT_CONFIG.w_time,
    )


def generate_conflict_explanations(
    risk: DimensionConflict,
    domain: DimensionConflict,
    relocation: DimensionConflict,
    time: DimensionConflict,
    is_high: bool,
    threshold: float = 0.40,
) -> Tuple[str, Dict[str, str]]:
    """Generate deterministic, human-readable explanations of family alignment and divergence."""
    explanations: Dict[str, str] = {}

    # Risk explanation
    if risk.gap > threshold:
        direction = "more risk-tolerant" if risk.student_value > risk.parent_value else "more cautious"
        explanations["risk"] = (
            f"Significant risk gap ({risk.gap:.0%}): Student is {direction} (student {risk.student_value:.2f} vs parent {risk.parent_value:.2f})."
        )
    else:
        explanations["risk"] = (
            f"Risk appetite is aligned ({risk.gap:.0%} difference)."
        )

    # Domain explanation
    if domain.gap > threshold:
        explanations["domain"] = (
            f"Career domain preferences diverge significantly ({domain.gap:.0%} average divergence across preferred sectors)."
        )
    else:
        explanations["domain"] = (
            f"Domain interest profiles show strong family alignment ({domain.gap:.0%} divergence)."
        )

    # Relocation explanation
    if relocation.gap > threshold:
        rel_diff = "open to relocating" if relocation.student_value > relocation.parent_value else "preferring to stay local"
        explanations["relocation"] = (
            f"Location preference mismatch ({relocation.gap:.0%}): Student is {rel_diff} relative to parent expectations."
        )
    else:
        explanations["relocation"] = (
            f"Location and relocation preferences are mutually acceptable ({relocation.gap:.0%} difference)."
        )

    # Time explanation
    if time.gap > threshold:
        explanations["time"] = (
            f"Timeline horizon gap: Student envisions up to {time.student_value:.1f} years until earning, whereas parent expects income within {time.parent_value:.1f} years."
        )
    else:
        explanations["time"] = (
            f"Time-to-income expectations match well (Student: {time.student_value:.1f}y, Parent: {time.parent_value:.1f}y)."
        )

    # Summary
    high_dims = [
        dim for dim, conflict in [("risk appetite", risk), ("domain preference", domain), ("relocation", relocation), ("time-to-income", time)]
        if conflict.gap > threshold
    ]
    if high_dims:
        summary = (
            f"High conflict detected primarily in {', '.join(high_dims)}. "
            "Deliberate discussion recommended on compromise career routes."
        )
    else:
        summary = "Family goals are substantially aligned across all core financial, risk, and lifestyle dimensions."

    return summary, explanations


def compute_overall_conflict(
    student: Any,
    parent: Any,
    config: ConflictConfig = DEFAULT_CONFIG,
) -> OverallConflictReport:
    """Compute the family-wide Conflict Index from student and parent profiles.

    Parameters
    ----------
    student
        A Student dataclass or dict with shared dimensions: risk_appetite, domain_preference,
        relocation_willingness, max_years_to_income.
    parent
        A ParentProfile or dict with risk, domain_ratings,
        relocation_willingness, max_years_to_income.
    config
        ConflictConfig with weights and thresholds.

    Returns
    -------
    OverallConflictReport
        Per-dimension conflicts, narrative diagnostics, and the weighted overall conflict [0, 1].
    """
    s_risk = getattr(student, "risk_appetite", None)
    if s_risk is None and isinstance(student, dict):
        s_risk = student.get("risk_appetite", 0.5)
    elif s_risk is None:
        s_risk = 0.5

    p_risk = getattr(parent, "risk", None)
    if p_risk is None and isinstance(parent, dict):
        p_risk = parent.get("risk", 0.5)
    elif p_risk is None:
        p_risk = 0.5

    s_pref = getattr(student, "domain_preference", None)
    if s_pref is None and isinstance(student, dict):
        s_pref = student.get("domain_preference", {})
    s_pref = s_pref or {}

    p_pref = getattr(parent, "domain_ratings", None)
    if p_pref is None and isinstance(parent, dict):
        p_pref = parent.get("domain_ratings", {})
    p_pref = p_pref or {}

    s_rel = getattr(student, "relocation_willingness", None)
    if s_rel is None and isinstance(student, dict):
        s_rel = student.get("relocation_willingness", 0.5)
    elif s_rel is None:
        s_rel = 0.5

    p_rel = getattr(parent, "relocation_willingness", None)
    if p_rel is None and isinstance(parent, dict):
        p_rel = parent.get("relocation_willingness", 0.5)
    elif p_rel is None:
        p_rel = 0.5

    s_years = getattr(student, "max_years_to_income", None)
    if s_years is None and isinstance(student, dict):
        s_years = student.get("max_years_to_income", 4.0)
    elif s_years is None:
        s_years = 4.0

    p_years = getattr(parent, "max_years_to_income", None)
    if p_years is None and isinstance(parent, dict):
        p_years = parent.get("max_years_to_income", 4.0)
    elif p_years is None:
        p_years = 4.0

    conflict_risk = _risk_conflict(float(s_risk), float(p_risk))
    conflict_domain = _domain_conflict(s_pref, p_pref)
    conflict_relocation = _relocation_conflict(float(s_rel), float(p_rel))
    conflict_time = _time_conflict(float(s_years), float(p_years))

    overall = (
        conflict_risk.gap * config.w_risk
        + conflict_domain.gap * config.w_domain
        + conflict_relocation.gap * config.w_relocation
        + conflict_time.gap * config.w_time
    )
    overall = _clamp(overall)

    is_high = any(
        c.gap > config.conflict_threshold
        for c in (conflict_risk, conflict_domain, conflict_relocation, conflict_time)
    )

    summary, explanations = generate_conflict_explanations(
        conflict_risk, conflict_domain, conflict_relocation, conflict_time, is_high, config.conflict_threshold
    )

    return OverallConflictReport(
        risk_conflict=conflict_risk,
        domain_conflict=conflict_domain,
        relocation_conflict=conflict_relocation,
        time_conflict=conflict_time,
        overall_conflict=overall,
        is_high_conflict=is_high,
        diagnosis_summary=summary,
        dimension_explanations=explanations,
    )


def _student_route_fit(
    student: Any,
    route: Any,
) -> Dict[str, float]:
    """Compute how well THIS route fits the student's shared-dimension preferences."""
    s_risk = getattr(student, "risk_appetite", None)
    if s_risk is None and isinstance(student, dict):
        s_risk = student.get("risk_appetite", 0.5)
    s_risk = float(s_risk if s_risk is not None else 0.5)

    s_pref = getattr(student, "domain_preference", None)
    if s_pref is None and isinstance(student, dict):
        s_pref = student.get("domain_preference", {})
    s_pref = s_pref or {}

    s_rel = getattr(student, "relocation_willingness", None)
    if s_rel is None and isinstance(student, dict):
        s_rel = student.get("relocation_willingness", 0.5)
    s_rel = float(s_rel if s_rel is not None else 0.5)

    s_years = getattr(student, "max_years_to_income", None)
    if s_years is None and isinstance(student, dict):
        s_years = student.get("max_years_to_income", 4.0)
    s_years = float(s_years if s_years is not None else 4.0)

    r_risk = getattr(route, "career_risk", None)
    if r_risk is None and isinstance(route, dict):
        r_risk = route.get("career_risk", 0.5)
    r_risk = float(r_risk if r_risk is not None else 0.5)

    r_domain = getattr(route, "domain", None)
    if r_domain is None and isinstance(route, dict):
        r_domain = route.get("domain", "unknown")
    r_domain = str(r_domain or "unknown")

    r_rel = getattr(route, "relocation_need", None)
    if r_rel is None and isinstance(route, dict):
        r_rel = route.get("relocation_need", 0.5)
    r_rel = float(r_rel if r_rel is not None else 0.5)

    r_years = getattr(route, "years_to_first_income", None)
    if r_years is None and isinstance(route, dict):
        r_years = route.get("years_to_first_income", 4.0)
    r_years = float(r_years if r_years is not None else 4.0)

    return {
        "risk": _clamp(1.0 - abs(s_risk - r_risk)),
        "domain": float(s_pref.get(r_domain, 3.0)) / DOMAIN_RATING_SCALE_MAX,
        "relocation": _clamp(1.0 - abs(s_rel - r_rel)),
        "time": _clamp(min(1.0, s_years / r_years)) if r_years > 0 else 1.0,
    }


def _parent_route_fit(
    parent: Any,
    route: Any,
    config: ConflictConfig = DEFAULT_CONFIG,
) -> Dict[str, float]:
    """Compute how well THIS route fits the parent's shared-dimension preferences."""
    p_risk = getattr(parent, "risk", None)
    if p_risk is None and isinstance(parent, dict):
        p_risk = parent.get("risk", 0.5)
    p_risk = float(p_risk if p_risk is not None else 0.5)

    p_pref = getattr(parent, "domain_ratings", None)
    if p_pref is None and isinstance(parent, dict):
        p_pref = parent.get("domain_ratings", {})
    p_pref = p_pref or {}

    p_rel = getattr(parent, "relocation_willingness", None)
    if p_rel is None and isinstance(parent, dict):
        p_rel = parent.get("relocation_willingness", 0.5)
    p_rel = float(p_rel if p_rel is not None else 0.5)

    p_years = getattr(parent, "max_years_to_income", None)
    if p_years is None and isinstance(parent, dict):
        p_years = parent.get("max_years_to_income", 4.0)
    p_years = float(p_years if p_years is not None else 4.0)

    r_risk = getattr(route, "career_risk", None)
    if r_risk is None and isinstance(route, dict):
        r_risk = route.get("career_risk", 0.5)
    r_risk = float(r_risk if r_risk is not None else 0.5)

    r_domain = getattr(route, "domain", None)
    if r_domain is None and isinstance(route, dict):
        r_domain = route.get("domain", "unknown")
    r_domain = str(r_domain or "unknown")

    r_rel = getattr(route, "relocation_need", None)
    if r_rel is None and isinstance(route, dict):
        r_rel = route.get("relocation_need", 0.5)
    r_rel = float(r_rel if r_rel is not None else 0.5)

    r_years = getattr(route, "years_to_first_income", None)
    if r_years is None and isinstance(route, dict):
        r_years = route.get("years_to_first_income", 4.0)
    r_years = float(r_years if r_years is not None else 4.0)

    return {
        "risk": _clamp(1.0 - abs(p_risk - r_risk)),
        "domain": float(p_pref.get(r_domain, 3.0)) / DOMAIN_RATING_SCALE_MAX,
        "relocation": _clamp(1.0 - abs(p_rel - r_rel)),
        "time": _clamp(min(1.0, p_years / r_years)) if r_years > 0 else 1.0,
    }


def compute_career_conflict(
    student: Any,
    parent: Any,
    route: Any,
    config: ConflictConfig = DEFAULT_CONFIG,
) -> CareerConflictReport:
    """Compute conflict for a specific career route.

    The insight: both sides may rate the SAME route, but differently.
    conflict = weighted gap between student-fit and parent-fit on the route.
    """
    s_fit = _student_route_fit(student, route)
    p_fit = _parent_route_fit(parent, route, config)

    gaps = {
        "risk": abs(s_fit["risk"] - p_fit["risk"]),
        "domain": abs(s_fit["domain"] - p_fit["domain"]),
        "relocation": abs(s_fit["relocation"] - p_fit["relocation"]),
        "time": abs(s_fit["time"] - p_fit["time"]),
    }

    career_conflict = (
        gaps["risk"] * config.w_risk
        + gaps["domain"] * config.w_domain
        + gaps["relocation"] * config.w_relocation
        + gaps["time"] * config.w_time
    )
    career_conflict = _clamp(career_conflict)

    is_high = any(v > config.conflict_threshold for v in gaps.values())

    c_id = getattr(route, "career_id", None) or (route.get("career_id") if isinstance(route, dict) else "unknown")
    r_id = getattr(route, "route_id", None) or (route.get("route_id") if isinstance(route, dict) else "unknown")

    return CareerConflictReport(
        career_id=str(c_id),
        route_id=str(r_id),
        student_risk_fit=round(s_fit["risk"], 4),
        student_domain_fit=round(s_fit["domain"], 4),
        student_relocation_fit=round(s_fit["relocation"], 4),
        student_time_fit=round(s_fit["time"], 4),
        parent_risk_fit=round(p_fit["risk"], 4),
        parent_domain_fit=round(p_fit["domain"], 4),
        parent_relocation_fit=round(p_fit["relocation"], 4),
        parent_time_fit=round(p_fit["time"], 4),
        risk_gap=round(gaps["risk"], 4),
        domain_gap=round(gaps["domain"], 4),
        relocation_gap=round(gaps["relocation"], 4),
        time_gap=round(gaps["time"], 4),
        career_conflict=round(career_conflict, 4),
        is_high_conflict=is_high,
    )


def evaluate_conflict(
    student: Any,
    parent: Any,
    routes: List[Any],
    config: ConflictConfig = DEFAULT_CONFIG,
) -> ConflictEvaluation:
    """Evaluate family conflict overall and per career route.

    This is the top-level entry point: one call returns the family diagnosis
    plus a conflict report for every route evaluated.
    """
    overall = compute_overall_conflict(student, parent, config)

    career_reports = [compute_career_conflict(student, parent, r, config) for r in routes]
    high_conflict_count = sum(1 for r in career_reports if r.is_high_conflict)
    avg_career_conflict = (
        sum(r.career_conflict for r in career_reports) / len(career_reports)
        if career_reports
        else 0.0
    )

    return ConflictEvaluation(
        overall=overall,
        career_conflicts=career_reports,
        num_high_conflict_careers=high_conflict_count,
        avg_career_conflict=round(avg_career_conflict, 4),
    )


# --- Blending & Negotiation Functions ---


def compute_composite_score(
    student_fit: float,
    family_viability: float,
    market_score: float = 0.50,
    career_conflict: float = 0.0,
    config: ConflictConfig = DEFAULT_CONFIG,
    w_student: float = 0.50,
    w_family: float = 0.50,
    w_market: float = 0.0,
) -> float:
    """Fix 1 & 8: Deleted composite conflict multiplier. Scoring uses two scores (Fit & Family)."""
    s = _clamp(student_fit)
    f = _clamp(family_viability)
    w_total = w_student + w_family
    if w_total <= 0:
        w_total = 1.0
    base = (w_student * s + w_family * f) / w_total
    return round(_clamp(base), 4)


def _compute_pareto_optimality(
    items: List[Tuple[int, float, float]]
) -> Dict[int, bool]:
    """Compute Pareto frontier for (student_fit, family_viability) pairs.

    A point A is Pareto dominated if there is another point B such that:
    B.student_fit >= A.student_fit AND B.family_viability >= A.family_viability
    with at least one strict inequality.
    """
    is_pareto: Dict[int, bool] = {idx: True for idx, _, _ in items}

    for i, s_i, f_i in items:
        for j, s_j, f_j in items:
            if i == j:
                continue
            if (s_j >= s_i and f_j >= f_i) and (s_j > s_i or f_j > f_i):
                is_pareto[i] = False
                break

    return is_pareto


def evaluate_negotiation_slider(
    student: Any,
    parent: Any,
    careers: List[Any],
    alpha: float = 0.50,
    min_student_fit: Optional[float] = None,
    min_family_viability: Optional[float] = None,
    config: ConflictConfig = DEFAULT_CONFIG,
) -> NegotiationResponse:
    """Evaluate candidate careers using the Negotiation Explorer slider.

    Parameters
    ----------
    student : Student profile or dict
    parent : Parent profile or dict
    careers : List of candidate career objects (with student_fit, family_viability, route data)
    alpha : float in [0, 1]
        0.0 = 100% Parent Priority
        1.0 = 100% Student Priority
        0.5 = Balanced / Compromise Priority
    min_student_fit : Optional[float]
        Threshold for compromise zone (default from config, in [0, 1] or [0, 100])
    min_family_viability : Optional[float]
        Threshold for compromise zone (default from config, in [0, 1] or [0, 100])
    config : ConflictConfig

    Returns
    -------
    NegotiationResponse
        Ranked careers, identified compromise zone options, and Pareto classifications.
    """
    alpha = _clamp(alpha)
    th_student = min_student_fit if min_student_fit is not None else config.min_student_fit_compromise
    th_family = min_family_viability if min_family_viability is not None else config.min_parent_viability_compromise

    # Normalize thresholds to [0, 1] if given on 0-100 scale
    if th_student > 1.0:
        th_student /= 100.0
    if th_family > 1.0:
        th_family /= 100.0

    overall_report = compute_overall_conflict(student, parent, config)

    # 1. Compute per-career fit_gap and extract metrics
    eval_items: List[Dict[str, Any]] = []
    points_for_pareto: List[Tuple[int, float, float]] = []

    for idx, c in enumerate(careers):
        career_id = getattr(c, "career_id", None) or (c.get("career_id") if isinstance(c, dict) else f"career_{idx}")
        route_id = getattr(c, "route_id", None) or (c.get("route_id") if isinstance(c, dict) else f"route_{idx}")
        name = getattr(c, "career_name", None) or (c.get("career_name") if isinstance(c, dict) else str(career_id))

        s_fit = float(getattr(c, "student_fit", None) or (c.get("student_fit") if isinstance(c, dict) else 0.5))
        f_viab = float(getattr(c, "family_viability", None) or (c.get("family_viability") if isinstance(c, dict) else 0.5))
        m_score = float(getattr(c, "market_score", None) or (c.get("market_score") if isinstance(c, dict) else 0.7))
        fin_ok = bool(getattr(c, "is_financially_viable", True) if not isinstance(c, dict) else c.get("is_financially_viable", True))
        status = getattr(c, "status", "ok") if not isinstance(c, dict) else c.get("status", "ok")

        # Conflict report for route (diagnosis only)
        c_report = compute_career_conflict(student, parent, c, config)

        # Fix 2: Rename per-career |Fit - Family| to fit_gap
        fit_gap_val = round(abs(s_fit - f_viab), 4)

        # Fix 1 & 8: Ranking = lambda*Fit + (1 - lambda)*Family. No conflict penalty!
        negotiated_score = round(_clamp(alpha * s_fit + (1.0 - alpha) * f_viab), 4)

        # Check qualification for compromise candidate pool (Fit >= threshold, Family >= threshold, fin_ok)
        qualifies_for_compromise = (s_fit >= th_student) and (f_viab >= th_family) and fin_ok and (status != "insufficient_data")

        stretch_val = bool(getattr(c, "stretch", False) if not isinstance(c, dict) else c.get("stretch", False))
        stretch_reasons = list(getattr(c, "stretch_reasons", []) if not isinstance(c, dict) else c.get("stretch_reasons", []))
        m_tier = str(getattr(c, "market_tier", "stable") if not isinstance(c, dict) else c.get("market_tier", "stable"))
        d_conf = str(getattr(c, "data_confidence", "high") if not isinstance(c, dict) else c.get("data_confidence", "high"))

        eval_items.append({
            "idx": idx,
            "career_id": str(career_id),
            "route_id": str(route_id),
            "career_name": str(name),
            "student_fit": round(s_fit, 4),
            "family_viability": round(f_viab, 4),
            "market_score": round(m_score, 4),
            "fit_gap": fit_gap_val,
            "negotiated_score": negotiated_score,
            "qualifies_for_compromise": qualifies_for_compromise,
            "is_financially_viable": fin_ok,
            "conflict_flag": c_report.is_high_conflict,
            "stretch": stretch_val,
            "stretch_reasons": stretch_reasons,
            "market_tier": m_tier,
            "data_confidence": d_conf,
            "status": status,
        })
        points_for_pareto.append((idx, s_fit, f_viab))

    # 2. Pareto analysis:
    # (a) Overall Pareto optimality across all items
    pareto_map = _compute_pareto_optimality(points_for_pareto)

    # (b) Fix 8: Compromise zone = Pareto frontier among qualifying careers (Fit >= 50, Family >= 50, fin_ok)
    compromise_candidate_points = [
        (item["idx"], item["student_fit"], item["family_viability"])
        for item in eval_items
        if item["qualifies_for_compromise"]
    ]
    compromise_pareto_map = _compute_pareto_optimality(compromise_candidate_points)

    # 3. Build CompromiseCareer models and reasons
    results: List[CompromiseCareer] = []
    for item in eval_items:
        idx = item["idx"]
        is_pareto = pareto_map.get(idx, False)
        in_compromise = item["qualifies_for_compromise"] and compromise_pareto_map.get(idx, False)
        s_fit = item["student_fit"]
        f_viab = item["family_viability"]
        gap = item["fit_gap"]

        if item["status"] == "insufficient_data":
            reason = "Excluded from compromise zone: insufficient financial data (missing salary or route cost)."
        elif not item["is_financially_viable"]:
            reason = "Financial gate failed: Career route exceeds family borrowing or repayment threshold."
        elif in_compromise:
            reason = (
                f"Compromise sweet spot: High student match ({s_fit:.0%}) and strong family viability ({f_viab:.0%}) "
                f"with manageable fit gap ({gap:.0%})."
            )
        elif s_fit > f_viab:
            reason = (
                f"Student preferred: Student fit is strong ({s_fit:.0%}), but family viability is lower ({f_viab:.0%})."
            )
        else:
            reason = (
                f"Parent preferred: Highly affordable and secure for family ({f_viab:.0%}), but lower student fit ({s_fit:.0%})."
            )

        results.append(
            CompromiseCareer(
                career_id=item["career_id"],
                route_id=item["route_id"],
                career_name=item["career_name"],
                student_fit=s_fit,
                family_viability=f_viab,
                market_score=item["market_score"],
                fit_gap=gap,
                negotiated_score=item["negotiated_score"],
                is_in_compromise_zone=in_compromise,
                is_pareto_optimal=is_pareto,
                is_financially_viable=item["is_financially_viable"],
                conflict_flag=item["conflict_flag"],
                stretch=item["stretch"],
                stretch_reasons=item["stretch_reasons"],
                market_tier=item["market_tier"],
                data_confidence=item["data_confidence"],
                summary_reason=reason,
            )
        )

    # 4. Fix 5 & 8: Sort descending by negotiated_score, with Market score as tiebreaker
    ranked = sorted(results, key=lambda x: (x.negotiated_score, x.market_score), reverse=True)
    compromise_zone = [c for c in ranked if c.is_in_compromise_zone]

    # Fix 8: Balanced pick = career maximizing min(Fit, Family)
    viable_candidates = [c for c in results if c.is_financially_viable]
    pick_pool = viable_candidates if viable_candidates else results
    balanced_pick = max(pick_pool, key=lambda c: (min(c.student_fit, c.family_viability), c.market_score)) if pick_pool else None
    balanced_pick_id = balanced_pick.career_id if balanced_pick else None

    return NegotiationResponse(
        alpha=alpha,
        total_careers_evaluated=len(ranked),
        compromise_zone_count=len(compromise_zone),
        ranked_careers=ranked,
        compromise_zone_careers=compromise_zone,
        family_diagnosis=overall_report.diagnosis_summary,
        balanced_pick_career_id=balanced_pick_id,
        balanced_pick=balanced_pick,
    )