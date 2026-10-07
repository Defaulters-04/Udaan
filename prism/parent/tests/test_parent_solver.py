"""Comprehensive pytest test suite for PRISM Parent Machine."""

import random
import pytest
from prism.parent.config import ParentSolverConfig, DEFAULT_CONFIG
from prism.parent.models import (
    ParentProfile,
    Route,
    SectorRatings,
    gl_to_risk,
)
from prism.parent.solver import (
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
from prism.parent.scores import (
    clamp,
    score_budget,
    score_repayment_burden,
    score_debt_service_ratio,
    calculate_payback,
    score_payback,
    score_financial,
    score_domain,
    score_sector,
    score_salary,
    score_time,
    score_location,
    score_aspiration,
    score_risk,
    score_family,
    evaluate_route,
    evaluate_parent_portfolio,
)


def test_1_sanity_case():
    """Sanity case from spec:

    S=3L, M=5k, Y=4, L_max=3L, M_inc=40k, E_exist=0, route cost 5L with no grant,
    Y1=7L, rate 10%, term 84 months.
    Expect:
    A_cash = 2.1L, L_need = 2.9L, EMI about 4814, RB = 0.12, DSR about 0.083,
    Payback about 3.57, F_payback about 0.554, F_budget about 0.02, F_financial about 59, G_fin = 1.
    """
    profile = ParentProfile(
        savings=300000.0,
        monthly_surplus=5000.0,
        household_income=40000.0,
        existing_emis=0.0,
        loan_max=300000.0,
        domain_ratings={"technology": 4},
        sector_ratings=SectorRatings(govt=3, private=4, entrepreneurship=3),
        min_salary=600000.0,
        max_years_to_income=5.0,
        relocation_willingness=0.8,
        risk=0.5,
    )

    route = Route(
        career_id="software_engineer",
        route_id="btech_cs_demo",
        tuition=350000.0,
        living=150000.0,
        exam_equipment=0.0,
        grant=0.0,
        duration_years=4.0,
        starting_salary=700000.0,
        years_to_first_income=4.0,
        career_risk=0.4,
        relocation_need=0.5,
        domain="technology",
        sector="private",
    )

    config = ParentSolverConfig(annual_loan_rate=0.10, loan_term_months=84)
    rep = evaluate_route(profile, route, config)

    # 1. A_cash = 2.1L (210,000)
    assert rep.cash_available == pytest.approx(210000.0, abs=1.0)

    # 2. L_need = 2.9L (290,000)
    assert rep.loan_needed == pytest.approx(290000.0, abs=1.0)

    # 3. EMI about 4814
    assert rep.emi == pytest.approx(4814.34, abs=2.0)

    # 4. RB = 0.12
    assert rep.repayment_burden == pytest.approx(0.1204, abs=0.005)

    # 5. DSR about 0.083
    assert rep.debt_service_ratio == pytest.approx(0.0825, abs=0.005)

    # 6. Payback about 3.57
    assert rep.payback_years == pytest.approx(3.5714, abs=0.01)

    # 7. F_payback about 0.554
    assert rep.sub_scores.f_payback == pytest.approx(0.5536, abs=0.005)

    # 8. F_budget about 0.02
    assert rep.sub_scores.f_budget == pytest.approx(0.0196, abs=0.005)

    # 9. F_financial about 59
    assert rep.f_financial == pytest.approx(58.99, abs=1.0)

    # 10. G_fin = 1
    assert rep.g_fin == 1
    assert rep.gate_cleared == 1
    assert rep.funding_gap == 0.0


def test_2_high_rb_fails_gate_and_shows_in_blocked_list():
    """A route with high RB fails G_fin and shows up in blocked list with the right reason."""
    profile = ParentProfile(
        savings=100000.0,
        monthly_surplus=2000.0,
        household_income=20000.0,  # Low monthly income
        existing_emis=8000.0,       # Already 40% RB
        loan_max=500000.0,
        domain_ratings={"design": 4},
        sector_ratings={"govt": 3, "private": 4, "entrepreneurship": 3},
        min_salary=400000.0,
        max_years_to_income=4.0,
        relocation_willingness=0.7,
        risk=0.4,
    )

    # Needs 4L loan, causing EMI ~ 6640 -> Total EMI 14640 / 20000 = 73.2% RB (> 50%)
    route = Route(
        career_id="ux_designer",
        route_id="expensive_design_school",
        tuition=400000.0,
        living=100000.0,
        duration_years=3.0,
        starting_salary=600000.0,
        years_to_first_income=3.0,
        career_risk=0.3,
        relocation_need=0.4,
        domain="design",
        sector="private",
    )

    response = evaluate_parent_portfolio(profile, [route], DEFAULT_CONFIG)
    assert len(response.blocked_list) == 1

    blocked = response.blocked_list[0]
    assert blocked.route_id == "expensive_design_school"
    assert any("Repayment burden" in r for r in blocked.block_reasons)
    assert blocked.shortfall_grant_needed > 0
    assert "grant/scholarship" in blocked.suggestion


def test_3_no_loan_needed_gives_emi_zero_and_dsr_rb_terms_equal_one():
    """A route with no loan need gives EMI = 0 and the DSR and RB terms equal 1."""
    profile = ParentProfile(
        savings=1000000.0,  # High savings
        monthly_surplus=20000.0,
        household_income=80000.0,
        existing_emis=0.0,
        loan_max=500000.0,
        domain_ratings={"science": 5},
        sector_ratings={"govt": 4, "private": 4, "entrepreneurship": 3},
        min_salary=500000.0,
        max_years_to_income=5.0,
        relocation_willingness=0.9,
        risk=0.5,
    )

    # Total cost 300k, Cash available is 0.5*1M + 12*3*0.25*20k = 500k + 180k = 680k
    route = Route(
        career_id="data_scientist",
        route_id="state_univ_bsc",
        tuition=200000.0,
        living=100000.0,
        duration_years=3.0,
        starting_salary=600000.0,
        years_to_first_income=3.0,
        career_risk=0.3,
        relocation_need=0.2,
        domain="science",
        sector="private",
    )

    rep = evaluate_route(profile, route, DEFAULT_CONFIG)

    assert rep.loan_needed == 0.0
    assert rep.emi == 0.0
    assert rep.repayment_burden == 0.0
    assert rep.debt_service_ratio == 0.0

    # DSR and RB subscore terms equal 1.0
    assert rep.sub_scores.f_repay_p == 1.0
    assert rep.sub_scores.f_dsr == 1.0
    assert rep.g_fin == 1
    assert rep.gate_cleared == 1


def test_4_best_route_selection_across_three_routes():
    """Best-route selection and alternatives ranking across 3 routes of one career."""
    profile = ParentProfile(
        savings=300000.0,
        monthly_surplus=6000.0,
        household_income=45000.0,
        existing_emis=2000.0,
        loan_max=400000.0,
        domain_ratings={"engineering": 5},
        sector_ratings={"govt": 4, "private": 5, "entrepreneurship": 3},
        min_salary=500000.0,
        max_years_to_income=5.0,
        relocation_willingness=0.8,
        risk=0.5,
    )

    # Route 1: Over-budget, exceeds loan_max -> Blocked
    r1 = Route(
        career_id="civil_engineer",
        route_id="expensive_private_inst",
        tuition=1000000.0,
        living=300000.0,
        duration_years=4.0,
        starting_salary=600000.0,
        years_to_first_income=4.0,
        career_risk=0.3,
        relocation_need=0.5,
        domain="engineering",
        sector="private",
    )

    # Route 2: Feasible, average starting salary
    r2 = Route(
        career_id="civil_engineer",
        route_id="state_engineering_college",
        tuition=300000.0,
        living=150000.0,
        duration_years=4.0,
        starting_salary=550000.0,
        years_to_first_income=4.0,
        career_risk=0.3,
        relocation_need=0.3,
        domain="engineering",
        sector="govt",
    )

    # Route 3: Feasible, lower cost, excellent starting salary -> Best route
    r3 = Route(
        career_id="civil_engineer",
        route_id="top_nit_college",
        tuition=250000.0,
        living=150000.0,
        duration_years=4.0,
        starting_salary=800000.0,
        years_to_first_income=4.0,
        career_risk=0.2,
        relocation_need=0.4,
        domain="engineering",
        sector="private",
    )

    res = evaluate_parent_portfolio(profile, [r1, r2, r3], DEFAULT_CONFIG)

    career_eval = res.career_results["civil_engineer"]
    assert career_eval.best_route is not None
    assert career_eval.best_route.route_id == "top_nit_college"
    assert career_eval.f_family_career > 0

    # Alternatives sorted by F_family descending
    assert len(career_eval.alternatives) == 3
    assert career_eval.alternatives[0].route_id == "top_nit_college"
    assert career_eval.alternatives[1].route_id == "state_engineering_college"
    assert career_eval.alternatives[2].route_id == "expensive_private_inst"

    # Blocked list contains r1
    assert len(res.blocked_list) == 1
    assert res.blocked_list[0].route_id == "expensive_private_inst"
    # Suggestion should point to cheaper alternative in same career
    assert "top_nit_college" in res.blocked_list[0].suggestion or "state_engineering_college" in res.blocked_list[0].suggestion


def test_5_edge_cases():
    """Verify all explicit edge cases: Y1<=0, M_inc<=0, t_r<=0, Sal_p<=0, A_family<=0, rate=0, missing domain."""
    config = DEFAULT_CONFIG

    # 1. Y1 <= 0
    dsr_val, w_dsr = calculate_debt_service_ratio(5000.0, 0.0)
    assert dsr_val == 1.0
    assert w_dsr is not None

    payback_val, w_pb = calculate_payback(200000.0, 0.0, config)
    assert payback_val == 99.0
    assert w_pb is not None

    sal_score, w_sal = score_salary(0.0, 500000.0)
    assert sal_score == 0.0
    assert w_sal is not None

    # 2. M_inc <= 0
    rb_val, w_rb = calculate_repayment_burden(2000.0, 3000.0, 0.0)
    assert rb_val == 1.0
    assert w_rb is not None

    rb_zero, _ = calculate_repayment_burden(0.0, 0.0, 0.0)
    assert rb_zero == 0.0

    # 3. t_r <= 0
    time_zero, w_tz = score_time(4.0, 0.0)
    assert time_zero == 1.0  # Spec: "If t_r = 0, f_time = 1"
    assert w_tz is None

    time_neg, w_tn = score_time(4.0, -1.0)
    assert time_neg == 1.0
    assert w_tn is not None

    # 4. Sal_p <= 0
    sal_p_zero, w_spz = score_salary(500000.0, 0.0)
    assert sal_p_zero == 1.0
    assert w_spz is not None

    # 5. A_family <= 0
    f_bud_zero, w_bz = score_budget(100000.0, 0.0)
    assert f_bud_zero == 0.0
    assert w_bz is not None

    f_bud_both_zero, _ = score_budget(0.0, 0.0)
    assert f_bud_both_zero == 1.0

    # 6. rate = 0 (EMI = L_need / n)
    config_rate_zero = ParentSolverConfig(annual_loan_rate=0.0, loan_term_months=100)
    emi_rate_zero = calculate_emi(500000.0, config_rate_zero)
    assert emi_rate_zero == pytest.approx(5000.0, abs=1e-4)

    # 7. missing domain rating
    dom_score, w_dom = score_domain(None, config)
    assert dom_score == 0.5
    assert w_dom is not None

    # 8. gl_to_risk helper validation
    assert gl_to_risk(13) == 0.0
    assert gl_to_risk(47) == 1.0
    assert gl_to_risk(30) == pytest.approx((30 - 13) / 34, abs=1e-5)
    with pytest.raises(ValueError):
        gl_to_risk(12)
    with pytest.raises(ValueError):
        gl_to_risk(48)


def test_6_property_test_score_ranges():
    """Property test: every sub-score is in [0, 1] and composites are in [0, 100] for random valid inputs."""
    random.seed(42)

    domains = ["technology", "healthcare", "commerce", "arts", "law"]
    sectors = ["govt", "private", "entrepreneurship"]

    for _ in range(100):
        s = random.uniform(0.0, 2000000.0)
        m = random.uniform(0.0, 100000.0)
        m_inc = random.uniform(10000.0, 300000.0)
        e_exist = random.uniform(0.0, 20000.0)
        l_max = random.uniform(0.0, 1500000.0)
        min_sal = random.uniform(200000.0, 1500000.0)
        t_p = random.uniform(1.0, 8.0)
        rho_p = random.uniform(0.0, 1.0)
        r_p = random.uniform(0.0, 1.0)

        dom_ratings = {d: random.randint(1, 5) for d in domains}
        sec_ratings = SectorRatings(
            govt=random.randint(1, 5),
            private=random.randint(1, 5),
            entrepreneurship=random.randint(1, 5),
        )

        profile = ParentProfile(
            savings=s,
            monthly_surplus=m,
            household_income=m_inc,
            existing_emis=e_exist,
            loan_max=l_max,
            domain_ratings=dom_ratings,
            sector_ratings=sec_ratings,
            min_salary=min_sal,
            max_years_to_income=t_p,
            relocation_willingness=rho_p,
            risk=r_p,
        )

        tuition = random.uniform(0.0, 2500000.0)
        living = random.uniform(0.0, 800000.0)
        exam_eq = random.uniform(0.0, 100000.0)
        grant = random.uniform(0.0, 500000.0)
        duration = random.uniform(1.0, 5.0)
        y1 = random.uniform(150000.0, 3000000.0)
        t_r = random.uniform(0.0, 6.0)
        r_c = random.uniform(0.0, 1.0)
        rho_c = random.uniform(0.0, 1.0)
        dom = random.choice(domains + ["unknown_domain"])
        sec = random.choice(sectors)
        g_acad = random.choice([0, 1])

        route = Route(
            career_id="test_career",
            route_id=f"route_{_}",
            tuition=tuition,
            living=living,
            exam_equipment=exam_eq,
            grant=grant,
            duration_years=duration,
            starting_salary=y1,
            years_to_first_income=t_r,
            career_risk=r_c,
            relocation_need=rho_c,
            domain=dom,
            sector=sec,
            g_acad=g_acad,
        )

        rep = evaluate_route(profile, route, DEFAULT_CONFIG)

        # Check sub-scores bounded in [0, 1]
        subs = rep.sub_scores
        for field_name in (
            "f_budget",
            "f_repay_p",
            "f_dsr",
            "f_payback",
            "f_domain",
            "f_sector",
            "f_salary",
            "f_time",
            "f_location",
        ):
            val = getattr(subs, field_name)
            assert 0.0 <= val <= 1.0, f"{field_name} out of bounds: {val}"

        # Check composites bounded in [0, 100]
        assert 0.0 <= rep.f_financial <= 100.0
        assert 0.0 <= rep.f_aspiration <= 100.0
        assert 0.0 <= rep.f_risk <= 100.0
        assert 0.0 <= rep.f_family <= 100.0

        # Gated property
        if rep.gate_cleared == 0:
            assert rep.f_family == 0.0


def test_7_academic_gate_interaction():
    """Verify academic gate g_acad multiplies into gate and zeroes F_family when 0."""
    profile = ParentProfile(
        savings=500000.0,
        monthly_surplus=10000.0,
        household_income=60000.0,
        existing_emis=0.0,
        loan_max=500000.0,
        domain_ratings={"science": 4},
        sector_ratings={"govt": 4, "private": 4, "entrepreneurship": 3},
        min_salary=500000.0,
        max_years_to_income=5.0,
        relocation_willingness=0.8,
        risk=0.5,
    )

    # Route that is financially easily viable, but g_acad = 0
    route = Route(
        career_id="physicist",
        route_id="bsc_physics",
        tuition=100000.0,
        living=50000.0,
        duration_years=3.0,
        starting_salary=600000.0,
        years_to_first_income=3.0,
        career_risk=0.3,
        relocation_need=0.2,
        domain="science",
        sector="private",
        g_acad=0,
    )

    rep = evaluate_route(profile, route, DEFAULT_CONFIG)
    assert rep.g_fin == 1
    assert rep.g_acad == 0
    assert rep.gate_cleared == 0
    assert rep.f_financial > 0.0
    assert rep.f_family == 0.0
    assert any("Academic gate failed" in r for r in rep.block_reasons)


def test_8_math_alias_and_property_accessors():
    """Verify initialization using math specification symbols and property accessors."""
    profile = ParentProfile(
        S=300000.0,
        M=5000.0,
        M_inc=40000.0,
        E_exist=0.0,
        L_max=300000.0,
        domain_ratings={"technology": 4},
        sector_ratings={"govt": 3, "private": 4, "entrepreneurship": 3},
        Sal_p=600000.0,
        T_p=5.0,
        rho_p=0.8,
        R_p=0.5,
    )

    assert profile.S == 300000.0
    assert profile.M == 5000.0
    assert profile.M_inc == 40000.0
    assert profile.E_exist == 0.0
    assert profile.L_max == 300000.0
    assert profile.Sal_p == 600000.0
    assert profile.T_p == 5.0
    assert profile.rho_p == 0.8
    assert profile.R_p == 0.5

    route = Route(
        career_id="software_engineer",
        route_id="btech_cs_demo",
        T=350000.0,
        L=150000.0,
        E_exam=0.0,
        G=0.0,
        Y=4.0,
        Y1=700000.0,
        t_r=4.0,
        R_c=0.4,
        rho_c=0.5,
        domain="technology",
        sector="private",
    )

    assert route.T == 350000.0
    assert route.L == 150000.0
    assert route.E_exam == 0.0
    assert route.G == 0.0
    assert route.Y == 4.0
    assert route.Y1 == 700000.0
    assert route.t_r == 4.0
    assert route.R_c == 0.4
    assert route.rho_c == 0.5

    rep = evaluate_route(profile, route, DEFAULT_CONFIG)
    assert rep.N_r == rep.cost_net
    assert rep.A_cash == rep.cash_available
    assert rep.L_need == rep.loan_needed
    assert rep.EMI == rep.emi
    assert rep.RB == rep.repayment_burden
    assert rep.DSR == rep.debt_service_ratio
    assert rep.Payback == rep.payback_years
    assert rep.G_fin == rep.g_fin
    assert rep.F_financial == rep.f_financial
    assert rep.F_aspiration == rep.f_aspiration
    assert rep.F_risk == rep.f_risk
    assert rep.F_family == rep.f_family


def test_9_sensitivity_analysis_overrides():
    """Verify +/-20% sensitivity parameter overrides via ParentSolverConfig."""
    cfg_base = DEFAULT_CONFIG

    # +20% and -20% variations
    cfg_high_savings = cfg_base.with_overrides(savings_share=cfg_base.savings_share * 1.20)
    cfg_low_savings = cfg_base.with_overrides(savings_share=cfg_base.savings_share * 0.80)

    assert cfg_high_savings.savings_share == pytest.approx(0.60, abs=1e-5)
    assert cfg_low_savings.savings_share == pytest.approx(0.40, abs=1e-5)

    cash_base = calculate_cash_available(100000.0, 5000.0, 4.0, cfg_base)
    cash_high = calculate_cash_available(100000.0, 5000.0, 4.0, cfg_high_savings)
    cash_low = calculate_cash_available(100000.0, 5000.0, 4.0, cfg_low_savings)

    assert cash_high > cash_base > cash_low


def test_10_grant_shortfall_remediation_efficacy():
    """Verify that applying a grant equal to calculated shortfall makes the route pass G_fin."""
    profile = ParentProfile(
        savings=100000.0,
        monthly_surplus=3000.0,
        household_income=30000.0,
        existing_emis=5000.0,
        loan_max=300000.0,
        domain_ratings={"data": 4},
        sector_ratings={"govt": 3, "private": 4, "entrepreneurship": 3},
        min_salary=500000.0,
        max_years_to_income=4.0,
        relocation_willingness=0.7,
        risk=0.4,
    )

    # Route that initially fails because loan needed exceeds loan_max
    route_initial = Route(
        career_id="data_analyst",
        route_id="costly_bootcamp_degree",
        tuition=600000.0,
        living=200000.0,
        exam_equipment=20000.0,
        grant=0.0,
        duration_years=3.0,
        starting_salary=600000.0,
        years_to_first_income=3.0,
        career_risk=0.3,
        relocation_need=0.5,
        domain="data",
        sector="private",
    )

    res_initial = evaluate_parent_portfolio(profile, [route_initial], DEFAULT_CONFIG)
    assert len(res_initial.blocked_list) == 1
    shortfall = res_initial.blocked_list[0].shortfall_grant_needed
    assert shortfall > 0.0

    # Create modified route with grant increased by exactly shortfall
    route_remediated = Route(
        career_id="data_analyst",
        route_id="costly_bootcamp_degree_remediated",
        tuition=600000.0,
        living=200000.0,
        exam_equipment=20000.0,
        grant=shortfall,
        duration_years=3.0,
        starting_salary=600000.0,
        years_to_first_income=3.0,
        career_risk=0.3,
        relocation_need=0.5,
        domain="data",
        sector="private",
    )

    res_remediated = evaluate_parent_portfolio(profile, [route_remediated], DEFAULT_CONFIG)
    assert len(res_remediated.blocked_list) == 0
    assert res_remediated.reports[0].g_fin == 1
    assert res_remediated.reports[0].gate_cleared == 1

