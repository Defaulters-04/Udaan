"""PRISM Engine - Market Machine Module.

Evaluates family-independent labour market viability, forecasting, and data confidence.
"""

from .config import MarketSolverConfig, DEFAULT_CONFIG
from .models import (
    DemandDataPoint,
    DemandSeries,
    CuratedTrend,
    SalaryBands,
    DisruptionProfile,
    RegionalTotals,
    CareerMarketRecord,
    ComponentDetail,
    MarketReport,
    MarketCatalogueResult,
    CareerScoreInput,
    RankedCareer,
    BlockedCareer,
    HandoffResult,
    CareerSensitivityResult,
    SensitivityResponse,
)
from .data_loader import (
    load_careers_snapshot,
    load_regional_totals_snapshot,
    load_meta_snapshot,
)
from .forecast import (
    clean_demand_series,
    forecast_demand_growth,
)
from .components import (
    clamp,
    calculate_percentile_ranks,
    calculate_trend_component,
    calculate_low_disruption,
    calculate_local_demand,
)
from .scores import (
    calculate_risk_proxy,
    build_explanation_string,
    evaluate_market_career,
    evaluate_market_catalogue,
)
from .handoff import (
    conflict_per_career,
    calculate_composite_score,
    calculate_final_score,
    rank_careers,
)
from .sensitivity import (
    run_market_sensitivity,
)

__all__ = [
    "MarketSolverConfig",
    "DEFAULT_CONFIG",
    "DemandDataPoint",
    "DemandSeries",
    "CuratedTrend",
    "SalaryBands",
    "DisruptionProfile",
    "RegionalTotals",
    "CareerMarketRecord",
    "ComponentDetail",
    "MarketReport",
    "MarketCatalogueResult",
    "CareerScoreInput",
    "RankedCareer",
    "BlockedCareer",
    "HandoffResult",
    "CareerSensitivityResult",
    "SensitivityResponse",
    "load_careers_snapshot",
    "load_regional_totals_snapshot",
    "load_meta_snapshot",
    "clean_demand_series",
    "forecast_demand_growth",
    "clamp",
    "calculate_percentile_ranks",
    "calculate_trend_component",
    "calculate_low_disruption",
    "calculate_local_demand",
    "calculate_risk_proxy",
    "build_explanation_string",
    "evaluate_market_career",
    "evaluate_market_catalogue",
    "conflict_per_career",
    "calculate_composite_score",
    "calculate_final_score",
    "rank_careers",
    "run_market_sensitivity",
]
