"""Pytest suite for PRISM Market Machine covering tests 1 through 15."""

import json
import random
import tempfile
from pathlib import Path
import pytest
import numpy as np

from prism.market.config import MarketSolverConfig, DEFAULT_CONFIG
from prism.market.models import (
    CareerMarketRecord,
    DemandSeries,
    DemandDataPoint,
    CuratedTrend,
    SalaryBands,
    DisruptionProfile,
    RegionalTotals,
    CareerScoreInput,
)
from prism.market.data_loader import (
    load_careers_snapshot,
    DEFAULT_DEMO_CAREERS_FILE,
)
from prism.market.components import (
    calculate_percentile_ranks,
    calculate_trend_component,
    calculate_low_disruption,
    calculate_local_demand,
)
from prism.market.forecast import (
    clean_demand_series,
    forecast_demand_growth,
)
from prism.market.scores import (
    evaluate_market_career,
    evaluate_market_catalogue,
    calculate_risk_proxy,
)
from prism.market.handoff import (
    conflict_per_career,
    calculate_composite_score,
    calculate_final_score,
    rank_careers,
)
from prism.market.sensitivity import run_market_sensitivity


def test_1_hand_calculated_main_case():
    """Test 1: Hand-calculated main case.

    Arithmetic:
    - demand_level = 0.50
    - trend = 0.65 (from g_low = 0.09 with defaults g_min = -0.30, g_max = 0.30: (0.09 - (-0.30))/0.60 = 0.65)
    - pay_yield = 0.75
    - D = 0.30 -> low_disruption = 1 - 0.30 = 0.70
    - local LQ = 1.0 -> local_demand = 1.0 / 2.0 = 0.50
    All 5 components available. Weights:
    0.25 (demand) + 0.30 (trend) + 0.20 (pay) + 0.15 (disruption) + 0.10 (local) = 1.00
    F_market = 100 * (0.25*0.50 + 0.30*0.65 + 0.20*0.75 + 0.15*0.70 + 0.10*0.50)
             = 100 * (0.125 + 0.195 + 0.150 + 0.105 + 0.050)
             = 100 * 0.625
             = 62.50
    """
    record = CareerMarketRecord(
        career_id="test_main_career",
        name="Main Hand-Calculated Career",
        curated_trend=CuratedTrend(
            growth_low=0.09,
            growth_central=0.15,
            growth_high=0.22,
            source_label="Curated Test Trend",
        ),
        salary=SalaryBands(
            p10=500000.0,
            p50=900000.0,
            p90=1600000.0,
            source_label="Curated Test Salary",
        ),
        typical_route_cost=300000.0,
        typical_duration_years=4.0,
        disruption=DisruptionProfile(score=0.30, rubric_version="v1.0", human_reviewed=True),
        regional_postings={"bengaluru": 100.0},
    )

    regional_totals = RegionalTotals(
        region_totals={"bengaluru": 50000.0},
        national_total=500000.0,
    )
    # With career national postings = 100 (only bengaluru), LQ = (100/100) / (50000/500000) = 1.0 / 0.1 = 10.
    # To get exact LQ = 1.0: career in bengaluru = 100, career national = 1000.
    record_exact = CareerMarketRecord(
        career_id="test_main_career_exact",
        name="Main Career Exact LQ 1",
        curated_trend=CuratedTrend(
            growth_low=0.09,
            growth_central=0.15,
            growth_high=0.22,
            source_label="Curated Test Trend",
        ),
        salary=SalaryBands(
            p10=500000.0,
            p50=900000.0,
            p90=1600000.0,
            source_label="Curated Test Salary",
        ),
        typical_route_cost=300000.0,
        typical_duration_years=4.0,
        disruption=DisruptionProfile(score=0.30, rubric_version="v1.0", human_reviewed=True),
        regional_postings={"bengaluru": 100.0, "other": 900.0},  # total 1000 -> 100/1000 = 0.10. LQ = 0.10 / 0.10 = 1.0
    )

    rep = evaluate_market_career(
        career_record=record_exact,
        demand_level_scaled=0.50,
        demand_level_quality="high",
        pay_yield_scaled=0.75,
        pay_yield_quality="high",
        regional_totals=regional_totals,
        student_region="bengaluru",
        config=DEFAULT_CONFIG,
    )

    assert rep.components["demand_level"].scaled == pytest.approx(0.50, abs=1e-5)
    assert rep.components["trend"].scaled == pytest.approx(0.65, abs=1e-5)
    assert rep.components["pay_yield"].scaled == pytest.approx(0.75, abs=1e-5)
    assert rep.components["low_disruption"].scaled == pytest.approx(0.70, abs=1e-5)
    assert rep.components["local_demand"].scaled == pytest.approx(0.50, abs=1e-5)
    assert rep.F_market == pytest.approx(62.50, abs=1e-2)


def test_2_same_case_without_local_data():
    """Test 2: Same case without local data.

    Weights renormalize over 0.90:
    - sum without local = 0.125 + 0.195 + 0.150 + 0.105 = 0.575
    - F_market = (0.575 / 0.90) * 100 = 63.888... approx 63.89
    - Local demand component unavailable, flag present, weights_used sum to 1.
    """
    record = CareerMarketRecord(
        career_id="test_no_local",
        name="No Local Career",
        curated_trend=CuratedTrend(
            growth_low=0.09,
            growth_central=0.15,
            growth_high=0.22,
            source_label="Curated Test Trend",
        ),
        salary=SalaryBands(
            p10=500000.0,
            p50=900000.0,
            p90=1600000.0,
            source_label="Curated Test Salary",
        ),
        typical_route_cost=300000.0,
        typical_duration_years=4.0,
        disruption=DisruptionProfile(score=0.30, rubric_version="v1.0", human_reviewed=True),
        regional_postings=None,
    )

    rep = evaluate_market_career(
        career_record=record,
        demand_level_scaled=0.50,
        demand_level_quality="high",
        pay_yield_scaled=0.75,
        pay_yield_quality="high",
        regional_totals=None,
        student_region=None,  # No local data requested
        config=DEFAULT_CONFIG,
    )

    assert rep.components["local_demand"].available is False
    assert rep.F_market == pytest.approx(63.89, abs=0.05)

    # Weights used must sum to 1.0
    total_weights_used = sum(rep.weights_used.values())
    assert total_weights_used == pytest.approx(1.0, abs=1e-3)
    assert any("student_region not specified" in f for f in rep.flags)


def test_3_percentile_rank_scaling_and_ties():
    """Test 3: Percentile rank on 5 distinct values gives 0, 0.25, 0.5, 0.75, 1;

    ties get average rank; N = 1 returns 0.5 with flag; N < 5 uses min-max.
    """
    cfg = DEFAULT_CONFIG

    # 1. 5 distinct values: (rank - 1) / (N - 1)
    vals_5 = [10.0, 20.0, 30.0, 40.0, 50.0]
    ranks_5, _ = calculate_percentile_ranks(vals_5, cfg)
    assert ranks_5 == pytest.approx([0.0, 0.25, 0.50, 0.75, 1.00], abs=1e-5)

    # 2. Ties get average rank
    # For [10, 20, 20, 40, 50]: ranks are 1, 2.5, 2.5, 4, 5
    # (2.5 - 1) / 4 = 1.5 / 4 = 0.375
    vals_ties = [10.0, 20.0, 20.0, 40.0, 50.0]
    ranks_ties, _ = calculate_percentile_ranks(vals_ties, cfg)
    assert ranks_ties[0] == pytest.approx(0.0, abs=1e-5)
    assert ranks_ties[1] == pytest.approx(0.375, abs=1e-5)
    assert ranks_ties[2] == pytest.approx(0.375, abs=1e-5)
    assert ranks_ties[3] == pytest.approx(0.75, abs=1e-5)
    assert ranks_ties[4] == pytest.approx(1.00, abs=1e-5)

    # 3. N = 1 returns 0.5 and flags it
    vals_1 = [42.0]
    ranks_1, flags_1 = calculate_percentile_ranks(vals_1, cfg)
    assert ranks_1 == [0.5]
    assert any("N=1" in f for f in flags_1)

    # 4. N < 5 uses min-max scaling
    vals_3 = [100.0, 150.0, 200.0]
    ranks_3, flags_3 = calculate_percentile_ranks(vals_3, cfg)
    assert ranks_3 == pytest.approx([0.0, 0.5, 1.0], abs=1e-5)
    assert any("min-max scaling" in f for f in flags_3)


def test_4_location_quotient():
    """Test 4: Location quotient: LQ = 1 gives 0.5, LQ = 2 gives 1, LQ = 4 capped at 1;

    zero totals make component unavailable.
    """
    totals = RegionalTotals(region_totals={"pune": 10000.0}, national_total=100000.0)

    # 1. LQ = 1 -> scaled 0.5
    # career in pune = 10, career national = 100 -> (10/100) / (10000/100000) = 0.10 / 0.10 = 1.0
    rec_lq1 = CareerMarketRecord(
        career_id="c1",
        name="C1",
        salary=SalaryBands(p10=1, p50=2, p90=3, source_label="S"),
        typical_route_cost=100000.0,
        disruption=DisruptionProfile(score=0.2),
        regional_postings={"pune": 10.0, "other": 90.0},
    )
    lq1, scaled1, _, _ = calculate_local_demand(rec_lq1, totals, "pune", DEFAULT_CONFIG)
    assert lq1 == pytest.approx(1.0, abs=1e-4)
    assert scaled1 == pytest.approx(0.5, abs=1e-4)

    # 2. LQ = 2 -> scaled 1.0
    # career in pune = 20, career national = 100 -> (20/100) / 0.10 = 2.0
    rec_lq2 = CareerMarketRecord(
        career_id="c2",
        name="C2",
        salary=SalaryBands(p10=1, p50=2, p90=3, source_label="S"),
        typical_route_cost=100000.0,
        disruption=DisruptionProfile(score=0.2),
        regional_postings={"pune": 20.0, "other": 80.0},
    )
    lq2, scaled2, _, _ = calculate_local_demand(rec_lq2, totals, "pune", DEFAULT_CONFIG)
    assert lq2 == pytest.approx(2.0, abs=1e-4)
    assert scaled2 == pytest.approx(1.0, abs=1e-4)

    # 3. LQ = 4 -> capped at 1.0
    rec_lq4 = CareerMarketRecord(
        career_id="c4",
        name="C4",
        salary=SalaryBands(p10=1, p50=2, p90=3, source_label="S"),
        typical_route_cost=100000.0,
        disruption=DisruptionProfile(score=0.2),
        regional_postings={"pune": 40.0, "other": 60.0},
    )
    lq4, scaled4, _, _ = calculate_local_demand(rec_lq4, totals, "pune", DEFAULT_CONFIG)
    assert lq4 == pytest.approx(4.0, abs=1e-4)
    assert scaled4 == pytest.approx(1.0, abs=1e-4)

    # 4. Zero totals make component unavailable
    zero_totals = RegionalTotals(region_totals={"pune": 0.0}, national_total=100000.0)
    _, scaled_zero, qual_zero, _ = calculate_local_demand(rec_lq1, zero_totals, "pune", DEFAULT_CONFIG)
    assert scaled_zero is None
    assert qual_zero == "none"


def test_5_forecast_ladder():
    """Test 5: Forecast ladder:

    - 36-month series uses ETS and g_low <= g_central <= g_high
    - 15-month series uses OLS with "short series" flag
    - 6-month series with curated_trend uses fallback and flags it
    - No data makes trend unavailable.
    """
    cfg = DEFAULT_CONFIG

    # 1. 36-month growing series -> ETS
    pts_36 = [DemandDataPoint(month=f"{2023 + i//12}-{1 + (i%12):02d}", count=100 + 5*i + (i%3)*4) for i in range(36)]
    series_36 = DemandSeries(points=pts_36, source_label="Adzuna", fetched_at="2026-10-01")
    s36_clean, _ = clean_demand_series(series_36)
    g_low, g_cen, g_high, method, vol, flags = forecast_demand_growth(s36_clean, None, cfg)
    assert method.startswith("ETS")
    assert g_low <= g_cen <= g_high
    assert vol >= 0.0

    # 2. 15-month series -> OLS with short series flag
    pts_15 = [DemandDataPoint(month=f"2025-{1 + (i%12):02d}" if i<12 else f"2026-{1 + (i-12):02d}", count=80 + 3*i) for i in range(15)]
    series_15 = DemandSeries(points=pts_15, source_label="Adzuna", fetched_at="2026-10-01")
    s15_clean, _ = clean_demand_series(series_15)
    g_low15, g_cen15, g_high15, method15, _, flags15 = forecast_demand_growth(s15_clean, None, cfg)
    assert method15.startswith("OLS")
    assert any("short series" in f for f in flags15)
    assert g_low15 <= g_cen15 <= g_high15

    # 3. 6-month series with curated trend -> Curated fallback
    pts_6 = [DemandDataPoint(month=f"2026-{i:02d}", count=50 + i) for i in range(1, 7)]
    series_6 = DemandSeries(points=pts_6, source_label="Adzuna", fetched_at="2026-10-01")
    curated = CuratedTrend(growth_low=0.05, growth_central=0.10, growth_high=0.15, source_label="Curated Industry")
    s6_clean, _ = clean_demand_series(series_6)
    g_low6, g_cen6, g_high6, method6, _, flags6 = forecast_demand_growth(s6_clean, curated, cfg)
    assert method6 == "curated_fallback"
    assert any("curated estimate" in f for f in flags6)
    assert g_low6 == 0.05

    # 4. No data -> Unavailable
    g_l_none, _, _, method_none, _, flags_none = forecast_demand_growth(None, None, cfg)
    assert method_none == "unavailable"
    assert g_l_none is None


def test_6_pessimism_ordering():
    """Test 6: Pessimism: for any series, F_market <= F_market_central <= F_market_optimistic."""
    careers = load_careers_snapshot(DEFAULT_DEMO_CAREERS_FILE)
    res = evaluate_market_catalogue(careers, config=DEFAULT_CONFIG)

    for rep in res.reports:
        assert rep.F_market <= rep.F_market_central <= rep.F_market_optimistic + 1e-4, (
            f"Career {rep.career_id} broke pessimism: {rep.F_market} <= {rep.F_market_central} <= {rep.F_market_optimistic}"
        )


def test_7_constant_zero_and_invalid_series_handling():
    """Test 7: Constant series, all-zero series, and series with NaN/negative values:

    no crash, defined fallback, flag present.
    """
    # 1. Constant series: zero variance handled cleanly
    pts_const = [DemandDataPoint(month=f"2024-{1+(i%12):02d}", count=200.0) for i in range(24)]
    s_const = DemandSeries(points=pts_const, source_label="Test", fetched_at="2026-10-01")
    s_clean_const, _ = clean_demand_series(s_const)
    g_low, g_cen, g_high, method, vol, flags = forecast_demand_growth(s_clean_const, None, DEFAULT_CONFIG)
    assert g_low == 0.0 and g_cen == 0.0 and g_high == 0.0
    assert vol == 0.0

    # 2. All-zero series: cleaned series treated as None with flag
    pts_zero = [DemandDataPoint(month=f"2024-{1+(i%12):02d}", count=0.0) for i in range(12)]
    s_zero = DemandSeries(points=pts_zero, source_label="Test", fetched_at="2026-10-01")
    s_clean_zero, flags_zero = clean_demand_series(s_zero)
    assert s_clean_zero is None
    assert any("only zero postings" in f for f in flags_zero)

    # 3. Series with negative and NaN values dropped
    pts_messy = [
        DemandDataPoint(month="2024-01", count=100.0),
        DemandDataPoint(month="2024-02", count=-50.0),  # Negative
        DemandDataPoint(month="2024-05", count=120.0),  # Gap > 2 months
    ]
    s_messy = DemandSeries(points=pts_messy, source_label="Test", fetched_at="2026-10-01")
    s_clean_messy, flags_messy = clean_demand_series(s_messy)
    assert len(s_clean_messy) == 2
    assert any("Dropped invalid/negative observation" in f for f in flags_messy)


def test_8_pay_yield_cost_floor_and_disordered_salary():
    """Test 8: Pay yield: zero cost uses cost_floor; disordered percentiles are flagged."""
    # 1. Zero cost govt route
    c_zero_cost = CareerMarketRecord(
        career_id="govt_ias",
        name="Govt IAS",
        salary=SalaryBands(p10=500000, p50=800000, p90=1500000, source_label="Official"),
        typical_route_cost=0.0,
        disruption=DisruptionProfile(score=0.1),
    )
    c_normal = CareerMarketRecord(
        career_id="private_eng",
        name="Private Eng",
        salary=SalaryBands(p10=300000, p50=600000, p90=1200000, source_label="Market"),
        typical_route_cost=300000.0,
        disruption=DisruptionProfile(score=0.3),
    )

    res = evaluate_market_catalogue([c_zero_cost, c_normal], config=DEFAULT_CONFIG)
    rep_govt = next(r for r in res.reports if r.career_id == "govt_ias")
    assert rep_govt.components["pay_yield"].available is True
    # Raw pay should use 50,000 cost floor: 800,000 / 50,000 = 16.0
    assert rep_govt.components["pay_yield"].raw == pytest.approx(16.0, abs=1e-4)

    # 2. Disordered percentiles: p10 > p50
    c_disordered = CareerMarketRecord(
        career_id="bad_sal",
        name="Bad Salary",
        salary=SalaryBands(p10=900000, p50=500000, p90=1200000, source_label="Curated"),
        typical_route_cost=100000.0,
        disruption=DisruptionProfile(score=0.2),
    )
    res_dis = evaluate_market_catalogue([c_disordered], config=DEFAULT_CONFIG)
    rep_dis = res_dis.reports[0]
    assert rep_dis.components["pay_yield"].quality == "low"


def test_9_monotonicity():
    """Test 9: Monotonicity:

    - Raising D never raises F_market (all else equal)
    - Raising g_low never lowers F_market (all else equal)
    """
    cfg = DEFAULT_CONFIG

    # Disruption monotonicity
    rep_d_low = evaluate_market_career(
        CareerMarketRecord(
            career_id="c_d_low",
            name="C D Low",
            curated_trend=CuratedTrend(growth_low=0.1, growth_central=0.15, growth_high=0.2, source_label="S"),
            salary=SalaryBands(p10=1, p50=2, p90=3, source_label="S"),
            typical_route_cost=100000.0,
            disruption=DisruptionProfile(score=0.20),
        ),
        demand_level_scaled=0.5, demand_level_quality="high",
        pay_yield_scaled=0.5, pay_yield_quality="high",
        regional_totals=None, student_region=None, config=cfg,
    )
    rep_d_high = evaluate_market_career(
        CareerMarketRecord(
            career_id="c_d_high",
            name="C D High",
            curated_trend=CuratedTrend(growth_low=0.1, growth_central=0.15, growth_high=0.2, source_label="S"),
            salary=SalaryBands(p10=1, p50=2, p90=3, source_label="S"),
            typical_route_cost=100000.0,
            disruption=DisruptionProfile(score=0.70),  # Higher disruption
        ),
        demand_level_scaled=0.5, demand_level_quality="high",
        pay_yield_scaled=0.5, pay_yield_quality="high",
        regional_totals=None, student_region=None, config=cfg,
    )
    assert rep_d_low.F_market >= rep_d_high.F_market

    # Growth monotonicity
    rep_g_low = evaluate_market_career(
        CareerMarketRecord(
            career_id="c_g_low",
            name="C G Low",
            curated_trend=CuratedTrend(growth_low=-0.10, growth_central=0.0, growth_high=0.10, source_label="S"),
            salary=SalaryBands(p10=1, p50=2, p90=3, source_label="S"),
            typical_route_cost=100000.0,
            disruption=DisruptionProfile(score=0.30),
        ),
        demand_level_scaled=0.5, demand_level_quality="high",
        pay_yield_scaled=0.5, pay_yield_quality="high",
        regional_totals=None, student_region=None, config=cfg,
    )
    rep_g_high = evaluate_market_career(
        CareerMarketRecord(
            career_id="c_g_high",
            name="C G High",
            curated_trend=CuratedTrend(growth_low=0.20, growth_central=0.25, growth_high=0.30, source_label="S"),
            salary=SalaryBands(p10=1, p50=2, p90=3, source_label="S"),
            typical_route_cost=100000.0,
            disruption=DisruptionProfile(score=0.30),
        ),
        demand_level_scaled=0.5, demand_level_quality="high",
        pay_yield_scaled=0.5, pay_yield_quality="high",
        regional_totals=None, student_region=None, config=cfg,
    )
    assert rep_g_high.F_market >= rep_g_low.F_market


def test_10_confidence_quality_labels_and_preservation():
    """Test 10: Confidence: a career with only curated data gets "low" overall and is still returned."""
    c_curated_only = CareerMarketRecord(
        career_id="curated_niche",
        name="Curated Niche Profession",
        demand_series=None,
        curated_trend=CuratedTrend(growth_low=0.02, growth_central=0.05, growth_high=0.08, source_label="Expert Estimate"),
        salary=SalaryBands(p10=100000, p50=200000, p90=300000, source_label="Curated Sample"),
        typical_route_cost=150000.0,
        disruption=DisruptionProfile(score=0.40, human_reviewed=False),
    )

    res = evaluate_market_catalogue([c_curated_only], config=DEFAULT_CONFIG)
    assert len(res.reports) == 1
    rep = res.reports[0]
    # Because demand series is missing, demand_level is none, trend is low, pay is medium, disruption is medium
    assert rep.overall_confidence == "low"
    # Never hidden or dropped
    assert len(res.low_confidence_careers) == 1
    assert res.low_confidence_careers[0].career_id == "curated_niche"


def test_11_property_test_score_ranges():
    """Test 11: Property test: for random valid inputs every component is in [0,1],

    every F is in [0,100], weights_used sum to 1, nothing is NaN.
    """
    rng = random.Random(42)

    careers = []
    for i in range(10):
        n_pts = rng.choice([0, 8, 16, 36])
        if n_pts > 0:
            pts = [DemandDataPoint(month=f"2024-{1+(m%12):02d}", count=float(rng.randint(50, 800))) for m in range(n_pts)]
            ds = DemandSeries(points=pts, source_label="Random", fetched_at="2026-10-01")
            curated = None
        else:
            ds = None
            curated = CuratedTrend(
                growth_low=rng.uniform(-0.25, 0.05),
                growth_central=rng.uniform(0.06, 0.15),
                growth_high=rng.uniform(0.16, 0.35),
                source_label="Curated",
            )

        p10 = rng.uniform(200000, 500000)
        p50 = p10 + rng.uniform(100000, 600000)
        p90 = p50 + rng.uniform(200000, 1000000)

        careers.append(
            CareerMarketRecord(
                career_id=f"rand_career_{i}",
                name=f"Random Career {i}",
                demand_series=ds,
                curated_trend=curated,
                salary=SalaryBands(p10=p10, p50=p50, p90=p90, source_label="Sample"),
                typical_route_cost=rng.uniform(0, 800000),
                disruption=DisruptionProfile(score=rng.uniform(0.0, 1.0)),
                regional_postings={"delhi": float(rng.randint(10, 100))} if rng.random() > 0.3 else None,
            )
        )

    totals = RegionalTotals(region_totals={"delhi": 50000.0}, national_total=400000.0)
    res = evaluate_market_catalogue(careers, regional_totals=totals, student_region="delhi")

    for rep in res.reports:
        # Check components in [0, 1]
        for cname, c in rep.components.items():
            if c.available and c.scaled is not None:
                assert 0.0 <= c.scaled <= 1.0, f"Component {cname} out of bounds: {c.scaled}"
                assert not np.isnan(c.scaled)

        # Check weights sum to 1.0
        assert sum(rep.weights_used.values()) == pytest.approx(1.0, abs=1e-3)

        # Check F in [0, 100]
        assert 0.0 <= rep.F_market <= 100.0
        assert 0.0 <= rep.F_market_central <= 100.0
        assert 0.0 <= rep.F_market_optimistic <= 100.0
        assert not np.isnan(rep.F_market)


def test_12_determinism():
    """Test 12: Determinism: same input and seed give identical output, including sensitivity."""
    careers = load_careers_snapshot(DEFAULT_DEMO_CAREERS_FILE)

    res1 = run_market_sensitivity(careers, n=200, seed=42)
    res2 = run_market_sensitivity(careers, n=200, seed=42)

    for cid in res1.results:
        assert res1.results[cid].top_3_stability_share == res2.results[cid].top_3_stability_share
        assert res1.results[cid].rank_shift_3_or_more_share == res2.results[cid].rank_shift_3_or_more_share


def test_13_snapshot_loader_validation():
    """Test 13: Snapshot loader rejects malformed JSON with message naming field; demo snapshot loads."""
    # 1. Demo snapshot loads cleanly
    careers = load_careers_snapshot(DEFAULT_DEMO_CAREERS_FILE)
    assert len(careers) == 8

    # 2. Malformed JSON with missing required field
    bad_data = [{"career_id": "c_bad", "name": "Bad"}]  # Missing salary, disruption, etc.
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as tmp:
        json.dump(bad_data, tmp)
        tmp_path = tmp.name

    with pytest.raises(ValueError) as excinfo:
        load_careers_snapshot(tmp_path)
    assert "field" in str(excinfo.value).lower() or "validation" in str(excinfo.value).lower()

    # 3. Duplicate career_id error
    dup_data = [
        {"career_id": "c_dup", "name": "Dup 1", "salary": {"p10":1, "p50":2, "p90":3, "source_label":"S"}, "typical_route_cost": 100, "disruption": {"score": 0.2}},
        {"career_id": "c_dup", "name": "Dup 2", "salary": {"p10":1, "p50":2, "p90":3, "source_label":"S"}, "typical_route_cost": 100, "disruption": {"score": 0.2}},
    ]
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as tmp:
        json.dump(dup_data, tmp)
        dup_path = tmp.name

    with pytest.raises(ValueError) as excinfo_dup:
        load_careers_snapshot(dup_path)
    assert "duplicate career_id" in str(excinfo_dup.value).lower()


def test_14_handoff_ranking_and_gating():
    """Test 14: Hand-off: conflict, composite and final match hand calculation;

    blocked careers are excluded from the ranking and listed with reasons.
    """
    # Career 1: F_student = 80, F_family = 60, F_market = 70
    # conflict = |80 - 60| = 20
    # composite = 0.45*80 + 0.35*60 + 0.20*70 = 36 + 21 + 14 = 71.0
    # final = 71 * (1 - 0.10 * 20 / 100) = 71 * (1 - 0.02) = 71 * 0.98 = 69.58
    inp1 = CareerScoreInput(career_id="viable_top", F_student=80.0, F_family=60.0, F_market=70.0, G_fin=1, G_acad=1)

    # Career 2: Financially blocked (G_fin = 0)
    inp2 = CareerScoreInput(career_id="blocked_fin", F_student=90.0, F_family=85.0, F_market=80.0, G_fin=0, G_acad=1)

    # Career 3: Academically blocked (G_acad = 0)
    inp3 = CareerScoreInput(career_id="blocked_acad", F_student=70.0, F_family=65.0, F_market=60.0, G_fin=1, G_acad=0)

    res = rank_careers([inp1, inp2, inp3], DEFAULT_CONFIG)

    # Ranked list contains only viable_top
    assert len(res.ranked) == 1
    top = res.ranked[0]
    assert top.career_id == "viable_top"
    assert top.conflict_score == pytest.approx(20.0, abs=1e-2)
    assert top.composite_score == pytest.approx(71.0, abs=1e-2)
    assert top.final_score == pytest.approx(69.58, abs=1e-2)

    # Blocked list contains both blocked careers with reasons
    assert len(res.blocked) == 2
    b_ids = [b.career_id for b in res.blocked]
    assert "blocked_fin" in b_ids
    assert "blocked_acad" in b_ids


def test_15_sensitivity_stability():
    """Test 15: Sensitivity: stability shares are between 0 and 1, and a career far ahead scores near 1."""
    # Create 4 careers: one dominant superstar career and 3 mediocre ones
    superstar = CareerMarketRecord(
        career_id="superstar",
        name="Superstar Career",
        curated_trend=CuratedTrend(growth_low=0.25, growth_central=0.28, growth_high=0.30, source_label="S"),
        salary=SalaryBands(p10=2000000, p50=3500000, p90=6000000, source_label="S"),
        typical_route_cost=100000.0,
        disruption=DisruptionProfile(score=0.05),
    )
    c2 = CareerMarketRecord(
        career_id="mediocre_1",
        name="Mediocre 1",
        curated_trend=CuratedTrend(growth_low=-0.20, growth_central=-0.10, growth_high=0.0, source_label="S"),
        salary=SalaryBands(p10=200000, p50=300000, p90=400000, source_label="S"),
        typical_route_cost=500000.0,
        disruption=DisruptionProfile(score=0.85),
    )
    c3 = CareerMarketRecord(
        career_id="mediocre_2",
        name="Mediocre 2",
        curated_trend=CuratedTrend(growth_low=-0.22, growth_central=-0.12, growth_high=0.0, source_label="S"),
        salary=SalaryBands(p10=200000, p50=310000, p90=410000, source_label="S"),
        typical_route_cost=500000.0,
        disruption=DisruptionProfile(score=0.82),
    )
    c4 = CareerMarketRecord(
        career_id="mediocre_3",
        name="Mediocre 3",
        curated_trend=CuratedTrend(growth_low=-0.24, growth_central=-0.14, growth_high=0.0, source_label="S"),
        salary=SalaryBands(p10=200000, p50=290000, p90=390000, source_label="S"),
        typical_route_cost=500000.0,
        disruption=DisruptionProfile(score=0.88),
    )

    sens = run_market_sensitivity([superstar, c2, c3, c4], n=500, seed=42)

    for cid, r in sens.results.items():
        assert 0.0 <= r.top_3_stability_share <= 1.0
        assert 0.0 <= r.rank_shift_3_or_more_share <= 1.0

    # Superstar career is far ahead, should stay in top 3 in 100% of runs
    assert sens.results["superstar"].top_3_stability_share >= 0.99
