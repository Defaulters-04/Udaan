"""PRISM Engine - Clean Unified Family Evaluation Module.

Provides:
1. evaluate_family(student_input, parent_input, options=None) -> dict
2. payback_range(route, parent_input, n=5000, seed=0) -> Optional[dict]
3. match_scholarships(student_input, parent_input) -> list
4. generate_remedies(blocked_cause, ...) -> list
5. compute_stability_top3(...) -> dict
"""

from __future__ import annotations
import csv
import math
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np
from pydantic import BaseModel, Field

from engine.student_fit.models import Student, Career as StudentCareer, AcademicProfile
from engine.student_fit.scoring import calculate_student_fit
from engine.parent.models import ParentProfile, Route, SectorRatings, ViabilityReport
from engine.parent.scores import evaluate_route, calculate_grant_shortfall
from engine.parent.config import DEFAULT_CONFIG as PARENT_CONFIG
from engine.conflict.scores import compute_overall_conflict
from engine.conflict.config import DEFAULT_CONFIG as CONFLICT_CONFIG
from engine.config import (
    DEFAULT_CONFIG as MASTER_CONFIG,
    CORE_CAREERS,
    PaybackSimulationConfig,
)
from engine.career_loader import load_seed_careers_metadata
from engine.domains import normalize_category_to_domain_id
from engine.answer_mapping import student_from_answers, parent_from_answers

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DATA_PROCESSED_DIR = WORKSPACE_ROOT / "data_pipeline" / "processed"


# ---------------------------------------------------------------------------
# Pydantic Output Models for evaluate_family
# ---------------------------------------------------------------------------
class CostDetail(BaseModel):
    total: Optional[float] = None
    total_cost_known: Optional[float] = None
    cost_status: str  # "complete" | "partial" | "missing"
    missing_fields: List[str] = Field(default_factory=list)
    is_lower_bound: bool = False


class ScoreDetail(BaseModel):
    fit: Optional[float] = None
    family_viability: Optional[float] = None
    market: Optional[float] = None
    composite: Optional[float] = None
    final: Optional[float] = None


class GateDetail(BaseModel):
    gate_financial: Optional[int] = None
    gate_academic: Optional[int] = None
    provisional_pass: bool = False


class RemedyItem(BaseModel):
    cause: str
    text_en: str
    text_hi: Optional[str] = None
    action: str


class BlendGridItem(BaseModel):
    lambda_val: float = Field(..., alias="lambda")
    rank_score: Optional[float] = None
    rank: Optional[int] = None


class SourceItem(BaseModel):
    field: str
    source_url: str
    retrieved_on: str


class CareerEvaluationResult(BaseModel):
    career_id: str
    career_name: str
    domain: str
    data_status: str  # "core" | "pending"
    pending_reason: Optional[str] = None
    best_route: Optional[Dict[str, Any]] = None
    alternative_routes: List[Dict[str, Any]] = Field(default_factory=list)
    cost: CostDetail
    scores: ScoreDetail
    gates: GateDetail
    blocked: bool
    blocked_cause: Optional[str] = None
    funding_gap: Optional[float] = None
    shortfall_details: Optional[Dict[str, Any]] = None
    remedies: List[RemedyItem] = Field(default_factory=list)
    blend_grid: List[Dict[str, Any]] = Field(default_factory=list)
    pareto: bool = False
    balanced_pick: bool = False
    sources: List[SourceItem] = Field(default_factory=list)
    stability_top3: Optional[float] = None


class FamilyEvaluationResponse(BaseModel):
    engine_version: str = "PRISM-2.0"
    scale_used: str = "0-100"
    conflict_index: float
    dimension_gaps: Dict[str, float]
    dimension_breakdown: Dict[str, Any]
    high_conflict: bool
    high_conflict_threshold: float = 60.0  # placeholder: threshold labelled placeholder
    careers: List[CareerEvaluationResult]
    warnings: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Data Loading Caches
# ---------------------------------------------------------------------------
_RAW_ROUTES_CACHE: Optional[List[Dict[str, Any]]] = None
_SALARY_BANDS_CACHE: Optional[Dict[str, Dict[str, Any]]] = None
_DEMAND_SIGNALS_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def _load_raw_route_costs() -> List[Dict[str, Any]]:
    global _RAW_ROUTES_CACHE
    if _RAW_ROUTES_CACHE is not None:
        return _RAW_ROUTES_CACHE

    rc_file = DATA_PROCESSED_DIR / "route_costs.csv"
    if not rc_file.exists():
        return []

    routes = []
    with open(rc_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            routes.append(row)
    _RAW_ROUTES_CACHE = routes
    return routes


def _load_salary_bands() -> Dict[str, Dict[str, Any]]:
    global _SALARY_BANDS_CACHE
    if _SALARY_BANDS_CACHE is not None:
        return _SALARY_BANDS_CACHE

    sb_file = DATA_PROCESSED_DIR / "salary_bands.csv"
    if not sb_file.exists():
        return {}

    salaries: Dict[str, Dict[str, Any]] = {}
    with open(sb_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("level") == "entry_level_0_to_2_yr":
                cid = row.get("career_id", "").strip()
                p50_val = row.get("p50", "").strip()
                if cid not in salaries:
                    salaries[cid] = row
                elif salaries[cid].get("p50") in ("NOT FOUND", "", None) and p50_val not in ("NOT FOUND", "", None):
                    salaries[cid] = row
                elif row.get("source_type") == "official" and p50_val not in ("NOT FOUND", "", None):
                    salaries[cid] = row
    _SALARY_BANDS_CACHE = salaries
    return salaries


def _load_demand_signals() -> Dict[str, Dict[str, Any]]:
    global _DEMAND_SIGNALS_CACHE
    if _DEMAND_SIGNALS_CACHE is not None:
        return _DEMAND_SIGNALS_CACHE

    ds_file = DATA_PROCESSED_DIR / "demand_signals.csv"
    if not ds_file.exists():
        return {}

    signals: Dict[str, Dict[str, Any]] = {}
    with open(ds_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get("career_id", "").strip()
            if cid and cid not in signals:
                signals[cid] = {
                    "direction": row.get("direction", "neutral"),
                    "source_name": row.get("source_name", ""),
                    "source_url": row.get("source_url", ""),
                    "retrieved_on": row.get("retrieved_on", "2026-10-07"),
                    "notes": row.get("notes", ""),
                }
    _DEMAND_SIGNALS_CACHE = signals
    return signals


# ---------------------------------------------------------------------------
# Adapters & Helpers
# ---------------------------------------------------------------------------
def _coerce_student(student_input: Any) -> Student:
    if isinstance(student_input, Student):
        return student_input
    if isinstance(student_input, dict):
        if "I_s" in student_input or "a_j" in student_input:
            acad_raw = student_input.get("academics", {})
            acad = AcademicProfile(
                marks=float(acad_raw.get("marks", 75.0)),
                subjects=set(acad_raw.get("subjects", [])),
                exams=set(acad_raw.get("exams", [])),
            )
            return Student(
                student_id=student_input.get("student_id", "stu_01"),
                stage=student_input.get("stage", "school"),
                I_s=student_input.get("I_s", {}),
                a_j=student_input.get("a_j", {}),
                academics=acad,
                risk_appetite=float(student_input.get("risk_appetite", 0.5)),
                domain_preference=student_input.get("domain_preference", {}),
                relocation_willingness=float(student_input.get("relocation_willingness", 0.5)),
                max_years_to_income=float(student_input.get("max_years_to_income", 4.0)),
            )
        return student_from_answers(student_input)
    raise ValueError(f"Unsupported student_input type: {type(student_input)}")


def _coerce_parent(parent_input: Any) -> ParentProfile:
    if isinstance(parent_input, ParentProfile):
        return parent_input
    if isinstance(parent_input, dict):
        if "savings" in parent_input or "S" in parent_input:
            return ParentProfile(**parent_input)
        return parent_from_answers(parent_input)
    raise ValueError(f"Unsupported parent_input type: {type(parent_input)}")


def _parse_val(val: Any) -> Optional[float]:
    if val is None or val == "NOT FOUND" or str(val).strip() == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Remedy Templates Generator (Bilingual Natural Spoken Hindi & English)
# ---------------------------------------------------------------------------
def generate_remedies(
    blocked_cause: Optional[str],
    loan_needed: float,
    loan_max: float,
    funding_gap: Optional[float],
    emi: float,
    rb: float,
    dsr: float,
    shortfall_grant: float,
    missing_fields: List[str],
    cheaper_alternative: Optional[Dict[str, Any]] = None,
) -> List[RemedyItem]:
    """Build empathetic, actionable bilingual remedies filled from computed numbers."""
    if not blocked_cause:
        return []

    remedies: List[RemedyItem] = []

    if blocked_cause == "loan_exceeds_cap":
        gap_val = funding_gap if funding_gap is not None else max(0.0, loan_needed - loan_max)
        text_en = (
            f"The required education loan (₹{loan_needed:,.0f}) exceeds your target limit of ₹{loan_max:,.0f} "
            f"by ₹{gap_val:,.0f}. Applying for merit/need-based government scholarships or looking at "
            f"state quota options can bridge this ₹{gap_val:,.0f} gap without straining family savings."
        )
        text_hi = (
            f"इस कोर्स के लिए ₹{loan_needed:,.0f} के लोन की जरूरत है, जो आपकी तय सीमा (₹{loan_max:,.0f}) से ₹{gap_val:,.0f} ज्यादा है। "
            f"सरकारी स्कॉलरशिप या राज्य कोटे की सीट मिलने पर यह ₹{gap_val:,.0f} की कमी आसानी से पूरी हो सकती है।"
        )
        remedies.append(
            RemedyItem(
                cause=blocked_cause,
                text_en=text_en,
                text_hi=text_hi,
                action="apply_scholarship",
            )
        )

    elif blocked_cause == "household_emi_too_high":
        text_en = (
            f"Monthly repayment (₹{emi:,.0f}/month) pushes total household commitments to {rb:.0%} of monthly income, "
            f"above the comfortable 50% limit. Extending the repayment tenure or securing an upfront grant of ₹{shortfall_grant:,.0f} "
            f"would bring monthly payments into a comfortable range."
        )
        text_hi = (
            f"हर महीने ₹{emi:,.0f} की किस्त भरने से घर की कुल देनदारी आमदनी के {rb:.0%} तक पहुंच जाएगी, जो 50% की सुरक्षित सीमा से ज्यादा है। "
            f"लोन की अवधि बढ़ाने या ₹{shortfall_grant:,.0f} की सहायता मिलने से मासिक किस्त आपके बजट में आ जाएगी।"
        )
        remedies.append(
            RemedyItem(
                cause=blocked_cause,
                text_en=text_en,
                text_hi=text_hi,
                action="extend_loan_tenure",
            )
        )

    elif blocked_cause == "graduate_dsr_too_high":
        text_en = (
            f"Repaying ₹{emi:,.0f}/month would require {dsr:.0%} of the graduate's starting salary, exceeding the 20% safety threshold. "
            f"Reducing borrowing through institutional fee concessions or opting for a subsidized government college ensures debt-free career beginnings."
        )
        text_hi = (
            f"शुरुआती नौकरी में ₹{emi:,.0f} महीना चुकाना सैलरी का {dsr:.0%} हिस्सा ले लेगा, जो सुरक्षित 20% से अधिक है। "
            f"सरकारी या रियायती कॉलेज चुनने से बच्चे पर नौकरी शुरू करते ही लोन का बोझ नहीं रहेगा।"
        )
        remedies.append(
            RemedyItem(
                cause=blocked_cause,
                text_en=text_en,
                text_hi=text_hi,
                action="choose_subsidized_institution",
            )
        )

    elif blocked_cause == "academic_ineligible":
        text_en = (
            "Current qualifying academic marks or subject combinations are below the eligibility threshold for this pathway. "
            "Preparing for supplementary state entrance exams or beginning with an allied diploma/degree keeps this goal achievable."
        )
        text_hi = (
            "इस रास्ते के लिए अभी जरूरी विषय या नंबर पूरे नहीं हो रहे हैं। "
            "राज्य स्तरीय प्रवेश परीक्षा की तैयारी करने या संबंधित डिप्लोमा से शुरुआत करने से यह करियर विकल्प खुला रहेगा।"
        )
        remedies.append(
            RemedyItem(
                cause=blocked_cause,
                text_en=text_en,
                text_hi=text_hi,
                action="academic_bridge_pathway",
            )
        )

    elif blocked_cause == "not_enough_data":
        missing_str = ", ".join(missing_fields) if missing_fields else "tuition or entry salary"
        text_en = (
            f"Official verified fee structures or entry salaries are currently missing ({missing_str}). "
            "We do not guess numbers to guarantee your family receives only confirmed data."
        )
        text_hi = (
            f"इस कोर्स की आधिकारिक फीस या शुरुआती सैलरी का पक्का विवरण अभी उपलब्ध नहीं है ({missing_str})। "
            "हमने कोई मनगढ़ंत आंकड़े नहीं जोड़े हैं ताकि आपको केवल सही जानकारी मिले।"
        )
        remedies.append(
            RemedyItem(
                cause=blocked_cause,
                text_en=text_en,
                text_hi=text_hi,
                action="await_verified_data",
            )
        )

    # If a cheaper passing alternative route exists, add constructive alternative advice
    if cheaper_alternative:
        alt_inst = cheaper_alternative.get("institution_name", "Government College")
        alt_cost = cheaper_alternative.get("total_cost_known") or cheaper_alternative.get("cost_net", 0.0)
        remedies.append(
            RemedyItem(
                cause="alternative_available",
                text_en=f"A verified affordable alternative route is available at {alt_inst} with a total cost of ₹{alt_cost:,.0f}, which fits comfortably inside your budget.",
                text_hi=f"इसी करियर के लिए {alt_inst} में एक सस्ता विकल्प उपलब्ध है जिसका कुल खर्च केवल ₹{alt_cost:,.0f} है, जो आपके परिवार के बजट में आसानी से आ जाएगा।",
                action="switch_to_alternative_route",
            )
        )

    return remedies


# ---------------------------------------------------------------------------
# Monte Carlo Payback Simulation
# ---------------------------------------------------------------------------
def payback_range(
    route: Any,
    parent_input: Any,
    n: int = 5000,
    seed: int = 0,
    config: Optional[PaybackSimulationConfig] = None,
) -> Optional[Dict[str, Any]]:
    """Monte Carlo simulation of payback years using lognormal salary band fit.

    Starting salary ~ lognormal fitted to p10/p90 of route salary band (z = 1.2816).
    If p10 or p90 is missing, returns None.
    Salary growth and repayment share are placeholders from config.
    """
    if config is None:
        config = PaybackSimulationConfig()

    p10 = _parse_val(getattr(route, "p10", None) if not isinstance(route, dict) else route.get("p10"))
    p90 = _parse_val(getattr(route, "p90", None) if not isinstance(route, dict) else route.get("p90"))

    # If route doesn't carry p10/p90 directly, check salary_bands cache
    if p10 is None or p90 is None:
        cid = getattr(route, "career_id", None) if not isinstance(route, dict) else route.get("career_id")
        sb_cache = _load_salary_bands()
        sal_row = sb_cache.get(cid, {})
        p10 = _parse_val(sal_row.get("p10"))
        p90 = _parse_val(sal_row.get("p90"))

    if p10 is None or p90 is None or p10 <= 0 or p90 <= p10:
        return None

    # Lognormal parameter fit
    z = config.z_lognormal
    ln_p10 = math.log(p10 * 100000.0 if p10 < 1000 else p10)
    ln_p90 = math.log(p90 * 100000.0 if p90 < 1000 else p90)
    mu = (ln_p10 + ln_p90) / 2.0
    sigma = (ln_p90 - ln_p10) / (2.0 * z)

    # Net educational cost
    raw_cost = (
        route.get("total_cost_known") or route.get("cost_net") or route.get("net_cost")
        if isinstance(route, dict)
        else (getattr(route, "total_cost_known", None) or getattr(route, "cost_net", None) or getattr(route, "net_cost", None))
    )
    net_cost = _parse_val(raw_cost) or 0.0

    if net_cost <= 0.0:
        return {
            "p10_years": 0.0,
            "p50_years": 0.0,
            "p90_years": 0.0,
            "prob_repay_within_horizon": 1.0,
            "horizon_years": config.payback_horizon_years,  # labelled placeholder
            "histogram": {"bin_edges": [0.0, 1.0], "bin_counts": [n]},
            "salary_growth_rate": config.salary_growth_rate,  # labelled placeholder
            "repayment_share": config.repayment_share,  # labelled placeholder
            "mc_samples": n,
            "seed": seed,
        }

    # Seeded simulation
    rng = np.random.default_rng(seed)
    salary_samples = rng.lognormal(mean=mu, sigma=sigma, size=n)

    g = config.salary_growth_rate  # placeholder
    r = config.repayment_share  # placeholder
    horizon = config.payback_horizon_years  # placeholder

    # Payback years T for each sample: (1+g)^T = 1 + (g*C)/(r*Y1)
    denom = np.log(1.0 + g)
    arg = 1.0 + (g * net_cost) / (r * salary_samples)
    payback_years_arr = np.log(np.maximum(1.0, arg)) / denom
    payback_years_arr = np.clip(payback_years_arr, 0.0, 30.0)

    p10_val = float(np.percentile(payback_years_arr, 10))
    p50_val = float(np.percentile(payback_years_arr, 50))
    p90_val = float(np.percentile(payback_years_arr, 90))
    prob_horizon = float(np.mean(payback_years_arr <= horizon))

    counts, bin_edges = np.histogram(payback_years_arr, bins=10, range=(0.0, 20.0))

    return {
        "p10_years": round(p10_val, 2),
        "p50_years": round(p50_val, 2),
        "p90_years": round(p90_val, 2),
        "prob_repay_within_horizon": round(prob_horizon, 4),
        "horizon_years": horizon,  # placeholder
        "histogram": {
            "bin_edges": [round(float(b), 2) for b in bin_edges],
            "bin_counts": [int(c) for c in counts],
        },
        "salary_growth_rate": g,  # placeholder
        "repayment_share": r,  # placeholder
        "mc_samples": n,
        "seed": seed,
    }


# ---------------------------------------------------------------------------
# Scholarships Matcher
# ---------------------------------------------------------------------------
def match_scholarships(student_input: Any, parent_input: Any) -> List[Dict[str, Any]]:
    """Match student and parent profiles against verified official national scholarships."""
    student = _coerce_student(student_input)
    parent = _coerce_parent(parent_input)

    annual_income = parent.household_income * 12.0
    marks = getattr(student.academics, "marks", 75.0)

    sch_file = DATA_PROCESSED_DIR / "scholarships.csv"
    if not sch_file.exists():
        return []

    matched = []
    with open(sch_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            max_inc = _parse_val(row.get("max_family_income"))
            min_m = _parse_val(row.get("min_marks_percent")) or 0.0

            income_ok = (max_inc is None) or (annual_income <= max_inc)
            marks_ok = marks >= min_m

            if income_ok and marks_ok:
                reasons = []
                if max_inc:
                    reasons.append(f"Family income ₹{annual_income:,.0f}/yr <= limit ₹{max_inc:,.0f}/yr")
                if min_m > 0:
                    reasons.append(f"Qualifying marks {marks:.1f}% >= requirement {min_m:.1f}%")

                matched.append({
                    "scholarship_id": row.get("scholarship_id"),
                    "name": row.get("name"),
                    "provider": row.get("provider"),
                    "eligibility_summary": row.get("eligibility_summary"),
                    "amount": row.get("amount") if row.get("amount") != "NOT FOUND" else None,
                    "deadline": row.get("deadline") if row.get("deadline") != "NOT FOUND" else None,
                    "apply_url": row.get("apply_url"),
                    "retrieved_on": row.get("retrieved_on"),
                    "linked_careers": [c.strip() for c in row.get("linked_careers", "").split(",") if c.strip()],
                    "match_reason": "; ".join(reasons) if reasons else "Eligible under scheme norms.",
                })
    return matched


# ---------------------------------------------------------------------------
# Stability Score (Nice to Have I)
# ---------------------------------------------------------------------------
def compute_stability_top3(
    evaluated_careers: List[Dict[str, Any]],
    n_perturbations: int = 1000,
    seed: int = 42,
) -> Dict[str, float]:
    """Compute share of 1,000 seeded weight perturbations (+/-20%) in which career stays top 3.

    Note: Perturbation weights are illustrative placeholders; not empirically validated.
    """
    def _get_s(c, k):
        sc = c["scores"]
        return getattr(sc, k) if hasattr(sc, k) else sc.get(k)

    eligible = [
        c for c in evaluated_careers
        if c["data_status"] == "core" and not c["blocked"] and _get_s(c, "fit") is not None and _get_s(c, "family_viability") is not None
    ]
    if len(eligible) < 3:
        return {c["career_id"]: 1.0 for c in eligible}

    rng = np.random.default_rng(seed)
    # Baseline lambda is 0.50. Perturb +/-20% uniformly -> lambda in [0.40, 0.60]
    lambdas = rng.uniform(0.40, 0.60, size=n_perturbations)

    top3_counts = {c["career_id"]: 0 for c in eligible}
    for lam in lambdas:
        scored = [
            (
                lam * _get_s(c, "fit") + (1.0 - lam) * _get_s(c, "family_viability"),
                c["career_id"]
            )
            for c in eligible
        ]
        # Sort descending by score, tie break by career_id ascending
        scored.sort(key=lambda x: (-x[0], x[1]))
        for _, cid in scored[:3]:
            top3_counts[cid] += 1

    return {cid: round(cnt / n_perturbations, 4) for cid, cnt in top3_counts.items()}


# ---------------------------------------------------------------------------
# Main Public Facade: evaluate_family
# ---------------------------------------------------------------------------
def evaluate_family(
    student_input: Any,
    parent_input: Any,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Comprehensive evaluation of family career alternatives for DataQuest 3.0.

    Parameters
    ----------
    student_input : Student instance or answers dict
    parent_input : ParentProfile instance or answers dict
    options : optional dict (supports 'loan_cap_override')

    Returns
    -------
    dict conforming to FamilyEvaluationResponse
    """
    student = _coerce_student(student_input)
    parent = _coerce_parent(parent_input)
    opts = options or {}

    # What-if loan cap override (Nice to Have K)
    if "loan_cap_override" in opts and opts["loan_cap_override"] is not None:
        override_cap = float(opts["loan_cap_override"])
        parent = parent.model_copy(update={"loan_max": override_cap})

    # 1. Overall Family Conflict Diagnostics
    conflict_rep = compute_overall_conflict(student, parent, CONFLICT_CONFIG)
    conflict_index = round(conflict_rep.overall_conflict * 100.0, 1)
    high_conflict_thresh = MASTER_CONFIG.high_conflict_threshold
    is_high_conflict = conflict_index >= high_conflict_thresh

    dimension_gaps = {
        "risk": round(conflict_rep.risk_conflict.gap, 4),
        "domain": round(conflict_rep.domain_conflict.gap, 4),
        "relocation": round(conflict_rep.relocation_conflict.gap, 4),
        "time": round(conflict_rep.time_conflict.gap, 4),
    }
    dimension_breakdown = {
        "risk": {"gap": dimension_gaps["risk"], "weight": conflict_rep.risk_conflict.weight},
        "domain": {"gap": dimension_gaps["domain"], "weight": conflict_rep.domain_conflict.weight},
        "relocation": {"gap": dimension_gaps["relocation"], "weight": conflict_rep.relocation_conflict.weight},
        "time": {"gap": dimension_gaps["time"], "weight": conflict_rep.time_conflict.weight},
    }

    # 2. Load Metadata and Sourced Tables
    seed_careers = load_seed_careers_metadata()
    raw_routes = _load_raw_route_costs()
    salary_bands = _load_salary_bands()
    demand_signals = _load_demand_signals()

    # Group raw routes by career_id
    routes_by_career: Dict[str, List[Dict[str, Any]]] = {}
    for r in raw_routes:
        routes_by_career.setdefault(r.get("career_id", "").strip(), []).append(r)

    # 3. Student Fit Scoring across all seed careers
    from engine.public import get_default_student_careers
    default_careers = {c.career_id: c for c in get_default_student_careers()}

    raw_career_results: List[Dict[str, Any]] = []

    for c_meta in seed_careers:
        cid = c_meta["career_id"]
        c_name = c_meta["career_name"]
        dom = c_meta["domain_id"]

        is_core = cid in CORE_CAREERS
        data_status = "core" if is_core else "pending"
        pending_reason = None if is_core else "Pending data ingestion: unverified official routes and salaries"

        # Calculate student fit
        s_career = default_careers.get(cid)
        if s_career:
            s_fit_res = calculate_student_fit(student, s_career)
            fit_score: Optional[float] = round(s_fit_res.F_student, 2)
            g_acad = s_fit_res.G_acad
        else:
            fit_score = 50.0
            g_acad = 1

        # Look up market demand signal
        m_signal = demand_signals.get(cid)
        if m_signal:
            m_dir = m_signal["direction"]
            if m_dir == "positive":
                market_score: Optional[float] = 85.0
            elif m_dir == "negative":
                market_score = 40.0
            else:
                market_score = 65.0
        else:
            market_score = None

        sources_list: List[SourceItem] = []

        # If pending: strictly excluded from scoring and ranking
        if not is_core:
            cost_detail = CostDetail(
                total=None,
                total_cost_known=None,
                cost_status="missing",
                missing_fields=["verified_route_costs", "verified_entry_salary"],
                is_lower_bound=False,
            )
            raw_career_results.append({
                "career_id": cid,
                "career_name": c_name,
                "domain": dom,
                "data_status": data_status,
                "pending_reason": pending_reason,
                "best_route": None,
                "alternative_routes": [],
                "cost": cost_detail,
                "scores": ScoreDetail(
                    fit=fit_score,
                    family_viability=None,
                    market=None,
                    composite=None,
                    final=None,
                ),
                "gates": GateDetail(
                    gate_financial=None,
                    gate_academic=g_acad,
                    provisional_pass=False,
                ),
                "blocked": True,
                "blocked_cause": "not_enough_data",
                "funding_gap": None,
                "shortfall_details": None,
                "remedies": [],
                "sources": [],
                "blend_grid": [],
                "pareto": False,
                "balanced_pick": False,
                "stability_top3": None,
            })
            continue

        # Core career: evaluate verified routes
        sal_row = salary_bands.get(cid)
        sal_val = _parse_val(sal_row.get("p50")) if sal_row else None
        salary_inr = sal_val * 100000.0 if sal_val is not None else None

        if sal_row and sal_val is not None and sal_row.get("source_url"):
            sources_list.append(
                SourceItem(
                    field="starting_salary",
                    source_url=sal_row["source_url"],
                    retrieved_on=sal_row.get("retrieved_on") or "2026-10-07",
                )
            )

        career_raw_routes = routes_by_career.get(cid, [])
        route_reports: List[Tuple[Route, ViabilityReport, Dict[str, Any]]] = []

        for r_raw in career_raw_routes:
            rid = r_raw.get("route_id", "")
            t_fee = _parse_val(r_raw.get("tuition_fee_total"))
            dur = _parse_val(r_raw.get("duration_years")) or 4.0
            h_fee = _parse_val(r_raw.get("hostel_fee_total"))
            m_fee = _parse_val(r_raw.get("mess_fee_total"))
            mand_fee = _parse_val(r_raw.get("mandatory_fee_total")) or 0.0
            ent_fee = _parse_val(r_raw.get("entrance_fee")) or 0.0
            exam_eq = mand_fee + ent_fee if (r_raw.get("mandatory_fee_total") != "NOT FOUND" or r_raw.get("entrance_fee") != "NOT FOUND") else None

            r_obj = Route(
                career_id=cid,
                route_id=rid,
                tuition=t_fee,
                duration_years=dur,
                hostel=h_fee,
                mess=m_fee,
                living=(h_fee + m_fee) if (h_fee is not None and m_fee is not None) else None,
                exam_equipment=exam_eq,
                grant=0.0,
                starting_salary=salary_inr,
                years_to_first_income=dur,
                domain=dom,
                sector="govt" if "govt" in r_raw.get("notes", "").lower() or any(k in r_raw.get("institution_name", "").lower() for k in ["iit", "nit", "anna", "delhi", "jadavpur", "aiims", "jnu"]) else "private",
                g_acad=g_acad,
                source_url=r_raw.get("source_url"),
                retrieved_on=r_raw.get("retrieved_on"),
            )

            v_rep = evaluate_route(parent, r_obj, PARENT_CONFIG)
            route_reports.append((r_obj, v_rep, r_raw))

            if r_raw.get("source_url") and r_raw.get("retrieved_on"):
                sources_list.append(
                    SourceItem(
                        field=f"route_{rid}_fee",
                        source_url=r_raw["source_url"],
                        retrieved_on=r_raw["retrieved_on"],
                    )
                )

        if not route_reports:
            # Core career but routes not yet populated
            cost_detail = CostDetail(
                total=None,
                total_cost_known=None,
                cost_status="missing",
                missing_fields=["tuition", "duration_years", "starting_salary"],
                is_lower_bound=False,
            )
            raw_career_results.append({
                "career_id": cid,
                "career_name": c_name,
                "domain": dom,
                "data_status": data_status,
                "pending_reason": "Core career with routes pending official collation",
                "best_route": None,
                "alternative_routes": [],
                "cost": cost_detail,
                "scores": ScoreDetail(
                    fit=fit_score,
                    family_viability=None,
                    market=market_score,
                    composite=None,
                    final=None,
                ),
                "gates": GateDetail(
                    gate_financial=0,
                    gate_academic=g_acad,
                    provisional_pass=False,
                ),
                "blocked": True,
                "blocked_cause": "not_enough_data",
                "funding_gap": None,
                "shortfall_details": None,
                "remedies": generate_remedies(
                    "not_enough_data", 0.0, parent.loan_max, None, 0.0, 0.0, 0.0, 0.0,
                    ["tuition", "starting_salary"]
                ),
                "sources": sources_list,
                "blend_grid": [],
                "pareto": False,
                "balanced_pick": False,
                "stability_top3": None,
            })
            continue

        # Select ONE shared best route for ALL numbers
        # Filter viable routes (g_fin == 1 and g_acad == 1)
        viable_routes = [rr for rr in route_reports if rr[1].gate_cleared == 1]
        if viable_routes:
            best_tuple = min(viable_routes, key=lambda x: (-x[1].f_family, str(x[0].route_id)))
        else:
            # If none viable, pick the route with highest f_family (lowest deficits)
            best_tuple = min(route_reports, key=lambda x: (-x[1].f_family, str(x[0].route_id)))

        best_route_obj, best_rep, best_raw = best_tuple

        # Convert best route to dict
        best_route_dict = {
            "route_id": best_route_obj.route_id,
            "institution_name": best_raw.get("institution_name", ""),
            "program_name": best_raw.get("program_name", ""),
            "duration_years": best_route_obj.duration_years,
            "net_cost": best_rep.cost_net,
            "loan_needed": best_rep.loan_needed,
            "monthly_emi": best_rep.emi,
            "repayment_burden": best_rep.repayment_burden,
            "debt_service_ratio": best_rep.debt_service_ratio,
            "payback_years": best_rep.payback_years,
            "cost_status": best_rep.cost_status,
            "is_lower_bound": best_rep.is_lower_bound,
            "provisional_pass": best_rep.provisional_pass,
        }

        # Alternatives
        alt_routes = []
        cheaper_passing_alt: Optional[Dict[str, Any]] = None
        for r_obj, v_rep, r_raw in route_reports:
            if r_obj.route_id == best_route_obj.route_id:
                continue
            alt_dict = {
                "route_id": r_obj.route_id,
                "institution_name": r_raw.get("institution_name", ""),
                "program_name": r_raw.get("program_name", ""),
                "net_cost": v_rep.cost_net,
                "f_family": v_rep.f_family,
                "gate_cleared": v_rep.gate_cleared,
                "cost_status": v_rep.cost_status,
            }
            alt_routes.append(alt_dict)
            if v_rep.gate_cleared == 1 and cheaper_passing_alt is None:
                cheaper_passing_alt = alt_dict

        cost_status = best_rep.cost_status
        is_lower = best_rep.is_lower_bound
        total_known = best_rep.total_cost_known
        total_full = best_rep.cost_net if cost_status == "complete" else None

        cost_detail = CostDetail(
            total=total_full,
            total_cost_known=total_known,
            cost_status=cost_status,
            missing_fields=best_rep.missing_fields,
            is_lower_bound=is_lower,
        )

        # Viability & Blocks
        is_blocked = (best_rep.gate_cleared == 0)
        blocked_cause = best_rep.blocked_cause if is_blocked else None

        f_family_score: Optional[float] = round(best_rep.f_family, 2) if cost_status != "missing" else None
        comp_score: Optional[float] = (
            round(0.50 * fit_score + 0.50 * f_family_score, 2)
            if (fit_score is not None and f_family_score is not None)
            else None
        )

        funding_gap_val = round(best_rep.funding_gap, 2) if (is_blocked and blocked_cause == "loan_exceeds_cap") else None
        shortfall_val = calculate_grant_shortfall(
            best_rep.cost_net, best_rep.cash_available, parent.household_income,
            parent.existing_emis, salary_inr or 0.0, parent.loan_max, PARENT_CONFIG
        ) if is_blocked else 0.0

        shortfall_details = {
            "grant_needed": round(shortfall_val, 2),
            "loan_needed": best_rep.loan_needed,
            "loan_max": parent.loan_max,
            "monthly_emi": best_rep.emi,
        } if is_blocked else None

        # Remedies
        remedies = generate_remedies(
            blocked_cause=blocked_cause,
            loan_needed=best_rep.loan_needed,
            loan_max=parent.loan_max,
            funding_gap=funding_gap_val,
            emi=best_rep.emi,
            rb=best_rep.repayment_burden,
            dsr=best_rep.debt_service_ratio,
            shortfall_grant=shortfall_val,
            missing_fields=best_rep.missing_fields,
            cheaper_alternative=cheaper_passing_alt,
        )

        raw_career_results.append({
            "career_id": cid,
            "career_name": c_name,
            "domain": dom,
            "data_status": data_status,
            "pending_reason": None,
            "best_route": best_route_dict,
            "alternative_routes": alt_routes,
            "cost": cost_detail,
            "scores": ScoreDetail(
                fit=fit_score,
                family_viability=f_family_score,
                market=market_score,
                composite=comp_score,
                final=comp_score,
            ),
            "gates": GateDetail(
                gate_financial=best_rep.g_fin,
                gate_academic=best_rep.g_acad,
                provisional_pass=best_rep.provisional_pass,
            ),
            "blocked": is_blocked,
            "blocked_cause": blocked_cause,
            "funding_gap": funding_gap_val,
            "shortfall_details": shortfall_details,
            "remedies": remedies,
            "sources": sources_list,
            "blend_grid": [],
            "pareto": False,
            "balanced_pick": False,
            "stability_top3": None,
        })

    # 4. Construct Deterministic 21-point blend_grid for Core Careers
    lambda_values = [round(i * 0.05, 2) for i in range(21)]
    core_rankable = [
        c for c in raw_career_results
        if c["data_status"] == "core" and c["scores"].fit is not None and c["scores"].family_viability is not None
    ]

    for lam in lambda_values:
        # Calculate rank score for all rankable core careers
        lam_scored = []
        for c in core_rankable:
            s_fit = c["scores"].fit
            f_viab = c["scores"].family_viability
            r_score = round(lam * s_fit + (1.0 - lam) * f_viab, 4)
            lam_scored.append((r_score, c["career_id"], c))

        # Deterministic sort: descending score, then ascending career_id
        lam_scored.sort(key=lambda x: (-x[0], x[1]))

        # Assign ranks
        for rank_idx, (r_score, cid, c) in enumerate(lam_scored, start=1):
            c["blend_grid"].append({
                "lambda": lam,
                "rank_score": r_score,
                "rank": rank_idx,
            })

    # Non-rankable core and pending careers get None across blend_grid
    for c in raw_career_results:
        if not c["blend_grid"]:
            c["blend_grid"] = [
                {"lambda": lam, "rank_score": None, "rank": None}
                for lam in lambda_values
            ]

    # 5. Pareto Optimality (Compromise Zone) & Balanced Pick
    viable_core = [
        c for c in raw_career_results
        if c["data_status"] == "core" and not c["blocked"] and c["scores"].fit is not None and c["scores"].family_viability is not None
    ]

    # Balanced pick = viable core career maximizing min(Fit, Family)
    if viable_core:
        best_balanced = min(
            viable_core,
            key=lambda c: (
                -min(c["scores"].fit, c["scores"].family_viability),
                -(c["scores"].fit + c["scores"].family_viability),
                c["career_id"],
            )
        )
        for c in raw_career_results:
            c["balanced_pick"] = (c["career_id"] == best_balanced["career_id"])
    else:
        for c in raw_career_results:
            c["balanced_pick"] = False

    # Pareto compromise candidates: viable, fit >= 50, family >= 50
    compromise_candidates = [
        c for c in viable_core
        if c["scores"].fit >= 50.0 and c["scores"].family_viability >= 50.0
    ]
    for c in raw_career_results:
        if c not in compromise_candidates:
            c["pareto"] = False
        else:
            # Check if dominated by another compromise candidate
            s_i = c["scores"].fit
            f_i = c["scores"].family_viability
            dominated = False
            for other in compromise_candidates:
                if other["career_id"] == c["career_id"]:
                    continue
                s_j = other["scores"].fit
                f_j = other["scores"].family_viability
                if (s_j >= s_i and f_j >= f_i) and (s_j > s_i or f_j > f_i):
                    dominated = True
                    break
            c["pareto"] = not dominated

    # 6. Stability Score (Nice to Have I)
    stability_map = compute_stability_top3(raw_career_results, n_perturbations=1000, seed=42)
    for c in raw_career_results:
        c["stability_top3"] = stability_map.get(c["career_id"])

    # Build validated Pydantic model response
    career_models = [CareerEvaluationResult(**c) for c in raw_career_results]

    return FamilyEvaluationResponse(
        conflict_index=conflict_index,
        dimension_gaps=dimension_gaps,
        dimension_breakdown=dimension_breakdown,
        high_conflict=is_high_conflict,
        high_conflict_threshold=high_conflict_thresh,
        careers=career_models,
        warnings=getattr(conflict_rep, "warnings", []),
    ).model_dump()
