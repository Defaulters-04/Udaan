"""Scoring functions and portfolio evaluation for PRISM Parent Machine."""

from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from .config import ParentSolverConfig, DEFAULT_CONFIG
from .models import (
    ParentProfile,
    Route,
    SubScores,
    ViabilityReport,
    BlockedRouteInfo,
    CareerEvaluation,
    ParentEvaluationResponse,
)
from .solver import (
    calculate_net_cost,
    calculate_cash_available,
    calculate_loan_needed,
    calculate_emi,
    calculate_repayment_burden,
    calculate_debt_service_ratio,
    calculate_family_affordability,
    check_financial_gate,
    calculate_grant_shortfall,
)


def clamp(val: float, low: float = 0.0, high: float = 1.0) -> float:
    """clamp(x) = max(low, min(high, x))."""
    return max(low, min(high, float(val)))


def score_budget(net_cost: float, family_affordability: float) -> Tuple[float, Optional[str]]:
    """F_budget = max(0, 1 - N_r / A_family)."""
    a_fam = float(family_affordability)
    n_r = float(net_cost)

    if a_fam <= 0.0:
        if n_r <= 0.0:
            return 1.0, "family_affordability A_family <= 0 and N_r == 0; F_budget set to 1.0"
        return 0.0, "family_affordability A_family <= 0; F_budget set to 0.0"

    raw = 1.0 - (n_r / a_fam)
    return clamp(raw, 0.0, 1.0), None


def score_repayment_burden(rb: float, config: ParentSolverConfig = DEFAULT_CONFIG) -> float:
    """F_repay_p = clamp(1 - max(0, RB - 0.30) / 0.20)."""
    excess = max(0.0, float(rb) - config.rb_comfort_threshold)
    penalty = excess / config.rb_penalty_range if config.rb_penalty_range > 0 else 0.0
    return clamp(1.0 - penalty, 0.0, 1.0)


def score_debt_service_ratio(dsr: float, config: ParentSolverConfig = DEFAULT_CONFIG) -> float:
    """F_dsr = clamp(1 - max(0, DSR - 0.10) / 0.10)."""
    excess = max(0.0, float(dsr) - config.dsr_comfort_threshold)
    penalty = excess / config.dsr_penalty_range if config.dsr_penalty_range > 0 else 0.0
    return clamp(1.0 - penalty, 0.0, 1.0)


def calculate_payback(
    net_cost: float, starting_salary: float, config: ParentSolverConfig = DEFAULT_CONFIG
) -> Tuple[float, Optional[str]]:
    """Payback = N_r / (0.20 * Y1) years."""
    n_r = float(net_cost)
    y1 = float(starting_salary)

    if y1 <= 0.0:
        if n_r <= 0.0:
            return 0.0, None
        return 99.0, "starting_salary Y1 <= 0; Payback horizon unbounded"

    annual_saving_rate = config.payback_income_share * y1
    if annual_saving_rate <= 0.0:
        return 99.0, "payback_income_share * Y1 <= 0; Payback horizon unbounded"

    return n_r / annual_saving_rate, None


def score_payback(payback_years: float, config: ParentSolverConfig = DEFAULT_CONFIG) -> float:
    """F_payback = max(0, 1 - Payback / 8)."""
    p = float(payback_years)
    horizon = config.payback_horizon_years
    if horizon <= 0.0:
        return 1.0 if p <= 0.0 else 0.0
    return clamp(1.0 - (p / horizon), 0.0, 1.0)


def score_financial(
    f_budget: float,
    f_repay_p: float,
    f_dsr: float,
    f_payback: float,
    config: ParentSolverConfig = DEFAULT_CONFIG,
) -> float:
    """F_financial = 100 * (0.35*F_budget + 0.25*F_repay_p + 0.25*F_dsr + 0.15*F_payback)."""
    composite = (
        config.w_budget * float(f_budget)
        + config.w_repay_p * float(f_repay_p)
        + config.w_dsr * float(f_dsr)
        + config.w_payback * float(f_payback)
    )
    return clamp(composite * 100.0, 0.0, 100.0)


def score_domain(rating: Optional[float], config: ParentSolverConfig = DEFAULT_CONFIG) -> Tuple[float, Optional[str]]:
    """f_domain = (rating of route's domain - 1)/4."""
    if rating is None:
        return 0.5, "Domain rating missing in parent profile; defaulted to 3 (f_domain=0.5)"

    r = float(rating)
    span = config.rating_max - config.rating_min
    if span <= 0.0:
        return 1.0, None

    normalized = (r - config.rating_min) / span
    return clamp(normalized, 0.0, 1.0), None


def score_sector(rating: Optional[float], config: ParentSolverConfig = DEFAULT_CONFIG) -> Tuple[float, Optional[str]]:
    """f_sector = (rating of route's sector - 1)/4."""
    if rating is None:
        return 0.5, "Sector rating missing or unmapped; defaulted to 3 (f_sector=0.5)"

    r = float(rating)
    span = config.rating_max - config.rating_min
    if span <= 0.0:
        return 1.0, None

    normalized = (r - config.rating_min) / span
    return clamp(normalized, 0.0, 1.0), None


def score_salary(starting_salary: float, min_salary: float) -> Tuple[float, Optional[str]]:
    """f_salary = min(1, Y1 / Sal_p)."""
    y1 = float(starting_salary)
    sal_p = float(min_salary)

    if sal_p <= 0.0:
        return 1.0, "min_salary Sal_p <= 0; f_salary defaulted to 1.0"

    if y1 <= 0.0:
        return 0.0, "starting_salary Y1 <= 0; f_salary set to 0.0"

    return clamp(min(1.0, y1 / sal_p), 0.0, 1.0), None


def score_time(max_years_to_income: float, years_to_first_income: float) -> Tuple[float, Optional[str]]:
    """f_time = min(1, T_p / t_r)."""
    t_r = float(years_to_first_income)
    t_p = float(max_years_to_income)

    if t_r == 0.0:
        return 1.0, None

    if t_r < 0.0:
        return 1.0, "years_to_first_income t_r < 0; f_time defaulted to 1.0"

    if t_p <= 0.0:
        return 0.0, "max_years_to_income T_p <= 0; f_time set to 0.0"

    return clamp(min(1.0, t_p / t_r), 0.0, 1.0), None


def score_location(relocation_need: float, relocation_willingness: float) -> float:
    """f_location = 1 - max(0, rho_c - rho_p)."""
    excess = max(0.0, float(relocation_need) - float(relocation_willingness))
    return clamp(1.0 - excess, 0.0, 1.0)


def score_aspiration(
    f_domain: float,
    f_sector: float,
    f_salary: float,
    f_time: float,
    f_location: float,
    config: ParentSolverConfig = DEFAULT_CONFIG,
) -> float:
    """F_aspiration = 100 * (0.30*f_domain + 0.15*f_sector + 0.20*f_salary + 0.20*f_time + 0.15*f_location)."""
    composite = (
        config.w_domain * float(f_domain)
        + config.w_sector * float(f_sector)
        + config.w_salary * float(f_salary)
        + config.w_time * float(f_time)
        + config.w_location * float(f_location)
    )
    return clamp(composite * 100.0, 0.0, 100.0)


def score_risk(career_risk: float, parent_risk: float) -> float:
    """F_risk = 100 * (1 - max(0, R_c - R_p))."""
    excess = max(0.0, float(career_risk) - float(parent_risk))
    return clamp((1.0 - excess) * 100.0, 0.0, 100.0)


def score_family(
    f_financial: float,
    f_aspiration: float,
    f_risk: float,
    gate: int,
    config: ParentSolverConfig = DEFAULT_CONFIG,
) -> float:
    """F_family(route) = G_fin * (0.50*F_financial + 0.30*F_aspiration + 0.20*F_risk)."""
    g_val = 1 if gate == 1 else 0
    composite = (
        config.w_financial * float(f_financial)
        + config.w_aspiration * float(f_aspiration)
        + config.w_risk * float(f_risk)
    )
    return clamp(float(g_val) * composite, 0.0, 100.0)


def evaluate_route(
    profile: ParentProfile, route: Route, config: ParentSolverConfig = DEFAULT_CONFIG
) -> ViabilityReport:
    """Evaluate full financial viability, sub-scores, and composite family fit for a route."""
    warnings: List[str] = []

    # 1. Financial Solver
    net_cost = calculate_net_cost(route.tuition, route.living, route.exam_equipment, route.grant)
    cash_available = calculate_cash_available(
        profile.savings, profile.monthly_surplus, route.duration_years, config
    )
    loan_needed = calculate_loan_needed(net_cost, cash_available)
    emi = calculate_emi(loan_needed, config)

    rb, w_rb = calculate_repayment_burden(profile.existing_emis, emi, profile.household_income)
    if w_rb:
        warnings.append(w_rb)

    dsr, w_dsr = calculate_debt_service_ratio(emi, route.starting_salary)
    if w_dsr:
        warnings.append(w_dsr)

    family_affordability = calculate_family_affordability(cash_available, profile.loan_max)
    g_fin, block_reasons = check_financial_gate(loan_needed, profile.loan_max, rb, dsr, config)

    # Academic gate and combined gate G = G_fin * g_acad
    g_acad = route.g_acad
    if g_acad == 0:
        block_reasons.append("Academic gate failed (g_acad=0)")
    gate_cleared = 1 if (g_fin == 1 and g_acad == 1) else 0

    funding_gap = max(0.0, loan_needed - profile.loan_max)

    # 2. Financial Sub-scores
    f_budget, w_budget = score_budget(net_cost, family_affordability)
    if w_budget:
        warnings.append(w_budget)

    f_repay_p = score_repayment_burden(rb, config)
    f_dsr = score_debt_service_ratio(dsr, config)

    payback_years, w_pb = calculate_payback(net_cost, route.starting_salary, config)
    if w_pb:
        warnings.append(w_pb)
    f_payback = score_payback(payback_years, config)

    f_financial = score_financial(f_budget, f_repay_p, f_dsr, f_payback, config)

    # 3. Aspirational Sub-scores
    dom_rating = profile.domain_ratings.get(route.domain)
    f_domain, w_dom = score_domain(dom_rating, config)
    if w_dom:
        warnings.append(w_dom)

    sec_rating: Optional[int] = None
    if isinstance(profile.sector_ratings, dict):
        sec_rating = profile.sector_ratings.get(route.sector.lower())
    else:
        sec_rating = profile.sector_ratings.get_rating(route.sector)
    f_sector, w_sec = score_sector(sec_rating, config)
    if w_sec:
        warnings.append(w_sec)

    f_salary, w_sal = score_salary(route.starting_salary, profile.min_salary)
    if w_sal:
        warnings.append(w_sal)

    f_time, w_time = score_time(profile.max_years_to_income, route.years_to_first_income)
    if w_time:
        warnings.append(w_time)

    f_location = score_location(route.relocation_need, profile.relocation_willingness)

    f_aspiration = score_aspiration(f_domain, f_sector, f_salary, f_time, f_location, config)

    # 4. Risk Score
    f_risk = score_risk(route.career_risk, profile.risk)

    # 5. Composite Family Score gated by G = G_fin * g_acad
    f_family = score_family(f_financial, f_aspiration, f_risk, gate_cleared, config)

    sub_scores = SubScores(
        f_budget=f_budget,
        f_repay_p=f_repay_p,
        f_dsr=f_dsr,
        f_payback=f_payback,
        f_domain=f_domain,
        f_sector=f_sector,
        f_salary=f_salary,
        f_time=f_time,
        f_location=f_location,
    )

    return ViabilityReport(
        career_id=route.career_id,
        route_id=route.route_id,
        cost_net=round(net_cost, 2),
        cash_available=round(cash_available, 2),
        loan_needed=round(loan_needed, 2),
        emi=round(emi, 2),
        repayment_burden=round(rb, 4),
        debt_service_ratio=round(dsr, 4),
        payback_years=round(payback_years, 2),
        g_fin=g_fin,
        g_acad=g_acad,
        gate_cleared=gate_cleared,
        sub_scores=sub_scores,
        f_financial=round(f_financial, 2),
        f_aspiration=round(f_aspiration, 2),
        f_risk=round(f_risk, 2),
        f_family=round(f_family, 2),
        funding_gap=round(funding_gap, 2),
        block_reasons=block_reasons,
        warnings=warnings,
    )


def evaluate_parent_portfolio(
    profile: ParentProfile, routes: List[Route], config: ParentSolverConfig = DEFAULT_CONFIG
) -> ParentEvaluationResponse:
    """Evaluate all routes across careers, ranking alternatives and constructing actionable blocked list."""
    reports: List[ViabilityReport] = [evaluate_route(profile, r, config) for r in routes]

    # Group reports by career_id
    career_reports: Dict[str, List[ViabilityReport]] = defaultdict(list)
    career_routes_map: Dict[str, Dict[str, Route]] = defaultdict(dict)

    for route, rep in zip(routes, reports):
        career_reports[rep.career_id].append(rep)
        career_routes_map[rep.career_id][rep.route_id] = route

    career_results: Dict[str, CareerEvaluation] = {}
    blocked_list: List[BlockedRouteInfo] = []

    for career_id, reps in career_reports.items():
        # Sort routes by F_family descending, then by net cost ascending
        sorted_reps = sorted(reps, key=lambda x: (x.f_family, -x.cost_net), reverse=True)

        viable_routes = [r for r in sorted_reps if r.gate_cleared == 1]
        best_route = viable_routes[0] if viable_routes else sorted_reps[0]
        max_f_family = best_route.f_family if viable_routes else 0.0

        career_results[career_id] = CareerEvaluation(
            career_id=career_id,
            best_route=best_route,
            f_family_career=round(max_f_family, 2),
            alternatives=sorted_reps,
        )

        # Check blocked routes in this career
        for rep in reps:
            if rep.g_fin == 0 or rep.gate_cleared == 0:
                target_route = career_routes_map[career_id][rep.route_id]
                shortfall = calculate_grant_shortfall(
                    rep.cost_net,
                    rep.cash_available,
                    profile.household_income,
                    profile.existing_emis,
                    target_route.starting_salary,
                    profile.loan_max,
                    config,
                )

                # Rule-based constructive suggestions
                cheaper_viable = [
                    v for v in viable_routes if v.route_id != rep.route_id and v.cost_net < rep.cost_net
                ]

                if cheaper_viable:
                    cheapest = min(cheaper_viable, key=lambda x: x.cost_net)
                    suggestion = (
                        f"Consider cheaper viable route '{cheapest.route_id}' in career '{career_id}' "
                        f"(net cost INR {cheapest.cost_net:,.0f}); otherwise, needs grant/scholarship of about "
                        f"INR {shortfall:,.0f} to bridge the shortfall for '{rep.route_id}'."
                    )
                else:
                    suggestion = (
                        f"Needs grant/scholarship of about INR {shortfall:,.0f} to achieve financial "
                        f"viability within family cash and loan limits."
                    )

                blocked_list.append(
                    BlockedRouteInfo(
                        career_id=career_id,
                        route_id=rep.route_id,
                        cost_net=rep.cost_net,
                        funding_gap=rep.funding_gap,
                        block_reasons=rep.block_reasons,
                        suggestion=suggestion,
                        shortfall_grant_needed=round(shortfall, 2),
                    )
                )

    return ParentEvaluationResponse(
        career_results=career_results, reports=reports, blocked_list=blocked_list
    )
