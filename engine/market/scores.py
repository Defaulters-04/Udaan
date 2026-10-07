"""Composite scoring and catalogue-wide evaluation for PRISM Market Machine."""

from datetime import datetime, date
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
import pandas as pd

from .config import MarketSolverConfig, DEFAULT_CONFIG
from .models import (
    CareerMarketRecord,
    RegionalTotals,
    ComponentDetail,
    MarketReport,
    MarketCatalogueResult,
)
from .forecast import clean_demand_series, forecast_demand_growth
from .components import (
    clamp,
    calculate_percentile_ranks,
    calculate_trend_component,
    calculate_low_disruption,
    calculate_local_demand,
)


def calculate_risk_proxy(disruption_score: float, volatility: float, config: MarketSolverConfig = DEFAULT_CONFIG) -> float:
    """risk_proxy = clamp(0.5 * D + 0.5 * clamp(volatility / 0.30)).

    NOTE: This risk_proxy is an output suggestion that the Parent machine may use
    for career risk R_c. Using disruption in both F_market and R_c double counts it;
    the team must choose one place.
    """
    d_term = float(disruption_score)
    vol_term = clamp(float(volatility) / config.volatility_scale, 0.0, 1.0)
    raw = (config.risk_proxy_weight_d * d_term) + (config.risk_proxy_weight_vol * vol_term)
    return clamp(raw, 0.0, 1.0)


def build_explanation_string(
    name: str,
    g_low: Optional[float],
    g_cen: Optional[float],
    g_high: Optional[float],
    trend_method: str,
    p10: float,
    p50: float,
    p90: float,
    salary_source: str,
    d_score: float,
    local_scaled: Optional[float],
    student_region: Optional[str],
) -> str:
    """Construct deterministic rule-based explanation string from computed values without LLM."""
    parts = []
    if g_low is not None and g_cen is not None and g_high is not None:
        parts.append(
            f"Postings are forecast to change between {g_low:+.1%} and {g_high:+.1%} over the next 12 months "
            f"(central {g_cen:+.1%}, method: {trend_method})."
        )
    else:
        parts.append(f"Demand trend is unavailable (method: {trend_method}).")

    parts.append(
        f"Salary band is p10 INR {p10:,.0f} / p50 INR {p50:,.0f} / p90 INR {p90:,.0f} (source: {salary_source})."
    )

    parts.append(f"Disruption exposure index D is {d_score:.2f} (automation resistance: {1.0 - d_score:.2f}).")

    if local_scaled is not None and student_region:
        parts.append(f"Local demand quotient in '{student_region}' scaled score is {local_scaled:.2f}.")

    return " ".join(parts)


def evaluate_market_career(
    career_record: CareerMarketRecord,
    demand_level_scaled: Optional[float],
    demand_level_quality: str,
    pay_yield_scaled: Optional[float],
    pay_yield_quality: str,
    regional_totals: Optional[RegionalTotals],
    student_region: Optional[str],
    config: MarketSolverConfig = DEFAULT_CONFIG,
    ref_date: Optional[date] = None,
) -> MarketReport:
    """Evaluate individual career market score, uncertainty variants, and confidence audit."""
    flags: List[str] = []
    sources: Dict[str, str] = {
        "salary": career_record.salary.source_label,
        "disruption_rubric": career_record.disruption.rubric_version,
        "disruption_human_reviewed": str(career_record.disruption.human_reviewed),
    }

    # 1. Clean demand series & forecast
    cleaned_series, clean_flags = clean_demand_series(career_record.demand_series, config.max_gap_fill_months)
    flags.extend(clean_flags)

    if career_record.demand_series:
        sources["demand"] = career_record.demand_series.source_label
        fetched_at = career_record.demand_series.fetched_at
        # Check staleness
        try:
            fetch_dt = datetime.strptime(fetched_at, "%Y-%m-%d").date()
            today = ref_date or date.today()
            age_days = (today - fetch_dt).days
            if age_days > config.max_snapshot_age_days:
                flags.append(f"stale data: demand snapshot is {age_days} days old (> {config.max_snapshot_age_days}d)")
        except Exception:
            pass
    elif career_record.curated_trend:
        sources["demand"] = career_record.curated_trend.source_label
        fetched_at = None
    else:
        sources["demand"] = "None"
        fetched_at = None

    g_low, g_cen, g_high, trend_method, volatility, forecast_flags = forecast_demand_growth(
        cleaned_series, career_record.curated_trend, config
    )
    flags.extend(forecast_flags)

    # 2. Compute individual components
    # (a) demand_level (supports series or curated fallback)
    if demand_level_scaled is not None:
        comp_demand_avail = True
        d_scaled = demand_level_scaled
        d_qual = demand_level_quality
    elif career_record.curated_trend is not None:
        comp_demand_avail = True
        d_scaled = 0.50
        d_qual = "low"
        flags.append("demand_level derived from curated fallback estimate")
    else:
        comp_demand_avail = False
        d_scaled = None
        d_qual = "none"

    comp_demand = ComponentDetail(
        name="demand_level",
        raw=float(cleaned_series.iloc[-12:].mean()) if (cleaned_series is not None and len(cleaned_series) >= 12) else None,
        scaled=d_scaled,
        weight_nominal=config.w_demand_level,
        weight_used=0.0,
        available=comp_demand_avail,
        quality=d_qual,
    )

    # (b) trend (scaled for low, central, high)
    trend_low = calculate_trend_component(g_low, config)
    trend_cen = calculate_trend_component(g_cen, config)
    trend_high = calculate_trend_component(g_high, config)
    comp_trend_avail = trend_low is not None

    if trend_method.startswith("ETS") and cleaned_series is not None and len(cleaned_series) >= config.min_points_seasonal:
        trend_qual = "high"
    elif trend_method.startswith("ETS") or trend_method.startswith("OLS") or trend_method == "constant_series":
        trend_qual = "medium"
    elif trend_method == "curated_fallback":
        trend_qual = "low"
    else:
        trend_qual = "none"

    comp_trend = ComponentDetail(
        name="trend",
        raw=g_low,
        scaled=trend_low,
        weight_nominal=config.w_trend,
        weight_used=0.0,
        available=comp_trend_avail,
        quality=trend_qual if comp_trend_avail else "none",
    )

    # (c) pay_yield
    comp_pay_avail = pay_yield_scaled is not None
    comp_pay = ComponentDetail(
        name="pay_yield",
        raw=career_record.salary.p50 / max(career_record.typical_route_cost, config.cost_floor),
        scaled=pay_yield_scaled,
        weight_nominal=config.w_pay_yield,
        weight_used=0.0,
        available=comp_pay_avail,
        quality=pay_yield_quality if comp_pay_avail else "none",
    )

    # (d) low_disruption
    d_score = career_record.disruption.score
    disr_scaled = calculate_low_disruption(d_score)
    disr_qual = "high" if career_record.disruption.human_reviewed else "low"
    comp_disr = ComponentDetail(
        name="low_disruption",
        raw=d_score,
        scaled=disr_scaled,
        weight_nominal=config.w_low_disruption,
        weight_used=0.0,
        available=True,
        quality=disr_qual,
    )

    # (e) local_demand
    lq_raw, local_scaled, local_qual, local_flags = calculate_local_demand(
        career_record, regional_totals, student_region, config
    )
    flags.extend(local_flags)
    comp_local_avail = local_scaled is not None
    comp_local = ComponentDetail(
        name="local_demand",
        raw=lq_raw,
        scaled=local_scaled,
        weight_nominal=config.w_local_demand,
        weight_used=0.0,
        available=comp_local_avail,
        quality=local_qual,
    )

    # 3. Renormalize weights over available components
    all_comps = {
        "demand_level": comp_demand,
        "trend": comp_trend,
        "pay_yield": comp_pay,
        "low_disruption": comp_disr,
        "local_demand": comp_local,
    }

    avail_weight_sum = sum(c.weight_nominal for c in all_comps.values() if c.available)
    weights_used: Dict[str, float] = {}

    if avail_weight_sum > 0.0:
        for k, c in all_comps.items():
            if c.available:
                w_used = c.weight_nominal / avail_weight_sum
                c.weight_used = round(w_used, 4)
                weights_used[k] = c.weight_used
            else:
                c.weight_used = 0.0
                weights_used[k] = 0.0
    else:
        weights_used = {k: 0.0 for k in all_comps}

    # 4. Compute F_market, F_market_central, F_market_optimistic
    sum_pessimistic = 0.0
    sum_central = 0.0
    sum_optimistic = 0.0

    for k, c in all_comps.items():
        if c.available and c.scaled is not None:
            w = weights_used[k]
            if k == "trend":
                sum_pessimistic += w * (trend_low if trend_low is not None else 0.0)
                sum_central += w * (trend_cen if trend_cen is not None else 0.0)
                sum_optimistic += w * (trend_high if trend_high is not None else 0.0)
            else:
                sum_pessimistic += w * c.scaled
                sum_central += w * c.scaled
                sum_optimistic += w * c.scaled

    f_market = clamp(sum_pessimistic * 100.0, 0.0, 100.0)
    f_central = clamp(sum_central * 100.0, 0.0, 100.0)
    f_optimistic = clamp(sum_optimistic * 100.0, 0.0, 100.0)

    # Ensure monotonicity F_market <= F_market_central <= F_market_optimistic
    if not (f_market <= f_central <= f_optimistic):
        sorted_fs = sorted([f_market, f_central, f_optimistic])
        f_market, f_central, f_optimistic = sorted_fs[0], sorted_fs[1], sorted_fs[2]

    # 5. Risk proxy
    risk_prox = calculate_risk_proxy(d_score, volatility, config)

    # 6. Overall confidence = weighted share of high or medium quality
    hm_weight = sum(
        c.weight_used for c in all_comps.values() if c.available and c.quality in ("high", "medium")
    )
    conf_score = round(hm_weight, 4)
    if conf_score >= config.confidence_high_threshold:
        overall_conf = "high"
    elif conf_score >= config.confidence_medium_threshold:
        overall_conf = "medium"
    else:
        overall_conf = "low"

    # 7. Explanation string
    sal = career_record.salary
    explanation = build_explanation_string(
        career_record.name,
        g_low,
        g_cen,
        g_high,
        trend_method,
        sal.p10,
        sal.p50,
        sal.p90,
        sal.source_label,
        d_score,
        comp_local.scaled,
        student_region,
    )

    return MarketReport(
        career_id=career_record.career_id,
        name=career_record.name,
        F_market=round(f_market, 2),
        F_market_central=round(f_central, 2),
        F_market_optimistic=round(f_optimistic, 2),
        components=all_comps,
        weights_used=weights_used,
        g_low=round(g_low, 4) if g_low is not None else None,
        g_central=round(g_cen, 4) if g_cen is not None else None,
        g_high=round(g_high, 4) if g_high is not None else None,
        trend_method=trend_method,
        volatility=round(volatility, 4),
        risk_proxy=round(risk_prox, 4),
        overall_confidence=overall_conf,
        confidence_score=conf_score,
        flags=flags,
        source_labels=sources,
        fetched_at=fetched_at,
        explanation=explanation,
    )


def evaluate_market_catalogue(
    careers: List[CareerMarketRecord],
    regional_totals: Optional[RegionalTotals] = None,
    student_region: Optional[str] = None,
    config: MarketSolverConfig = DEFAULT_CONFIG,
    ref_date: Optional[date] = None,
) -> MarketCatalogueResult:
    """Evaluate market scores for an entire catalogue of careers."""
    if not careers:
        return MarketCatalogueResult(reports=[], sorted_careers=[], low_confidence_careers=[])

    # 1. Collect catalogue-level metrics for percentile ranking
    base_levels: List[Optional[float]] = []
    log_pays: List[Optional[float]] = []
    pay_qualities: List[str] = []
    demand_qualities: List[str] = []

    for c in careers:
        # Base demand level
        s, _ = clean_demand_series(c.demand_series, config.max_gap_fill_months)
        if s is not None and len(s) > 0:
            if len(s) >= 12:
                base = float(s.iloc[-12:].mean())
                d_qual = "high"
            else:
                base = float(s.mean())
                d_qual = "low"
            base_levels.append(base)
            demand_qualities.append(d_qual)
        else:
            base_levels.append(None)
            demand_qualities.append("none")

        # Pay yield: ln(p50 / max(route_cost, cost_floor))
        sal = c.salary
        cost_eff = max(float(c.typical_route_cost), config.cost_floor)
        if sal.p50 > 0:
            pay_raw = sal.p50 / cost_eff
            log_pays.append(float(np.log(max(1e-9, pay_raw))))

            if not (sal.p10 <= sal.p50 <= sal.p90):
                pay_qualities.append("low")
            elif "curated" in sal.source_label.lower():
                pay_qualities.append("medium")
            else:
                pay_qualities.append("high")
        else:
            log_pays.append(None)
            pay_qualities.append("none")

    # 2. Percentile ranking across catalogue
    demand_scaled_list, d_rank_flags = calculate_percentile_ranks(base_levels, config)
    pay_scaled_list, p_rank_flags = calculate_percentile_ranks(log_pays, config)

    # 3. Evaluate each career
    reports: List[MarketReport] = []
    for idx, c in enumerate(careers):
        rep = evaluate_market_career(
            c,
            demand_scaled_list[idx],
            demand_qualities[idx],
            pay_scaled_list[idx],
            pay_qualities[idx],
            regional_totals,
            student_region,
            config,
            ref_date,
        )
        if d_rank_flags:
            rep.flags.extend(d_rank_flags)
        if p_rank_flags:
            rep.flags.extend(p_rank_flags)
        reports.append(rep)

    # 4. Sort reports descending by F_market
    sorted_reports = sorted(reports, key=lambda x: x.F_market, reverse=True)
    low_conf_reports = [r for r in sorted_reports if r.overall_confidence == "low"]

    return MarketCatalogueResult(
        reports=reports,
        sorted_careers=sorted_reports,
        low_confidence_careers=low_conf_reports,
    )
