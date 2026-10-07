"""Demand series cleaning and deterministic forecasting ladder for PRISM Market Machine."""

from typing import Tuple, List, Optional
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.exponential_smoothing.ets import ETSModel

from .config import MarketSolverConfig, DEFAULT_CONFIG
from .models import DemandSeries, CuratedTrend


def clean_demand_series(
    demand_series: Optional[DemandSeries],
    max_gap_fill_months: int = 2,
) -> Tuple[Optional[pd.Series], List[str]]:
    """Clean monthly demand series by sorting, dropping invalid values, and linearly interpolating short gaps."""
    flags: List[str] = []
    if demand_series is None or not demand_series.points:
        return None, ["Missing or empty demand series"]

    # 1. Extract and validate points
    valid_points = []
    for pt in demand_series.points:
        if pt.count is not None and not np.isnan(pt.count) and pt.count >= 0:
            valid_points.append((pt.month, float(pt.count)))
        else:
            flags.append(f"Dropped invalid/negative observation in month '{pt.month}'")

    if not valid_points:
        return None, flags + ["All observations were invalid or negative"]

    # Sort strictly by month YYYY-MM
    valid_points.sort(key=lambda x: x[0])

    # Convert to Month PeriodIndex to identify missing months
    months = [pd.Period(m, freq="M") for m, _ in valid_points]
    counts = [c for _, c in valid_points]

    month_dict = {}
    for m, c in zip(months, counts):
        month_dict[m] = c

    min_month = min(months)
    max_month = max(months)
    full_range = pd.period_range(min_month, max_month, freq="M")

    s_sparse = pd.Series(index=full_range, dtype=float)
    for m in full_range:
        if m in month_dict:
            s_sparse[m] = month_dict[m]

    is_missing = s_sparse.isna()
    if is_missing.any():
        gap_streak = 0
        can_interpolate = True
        for m in full_range:
            if pd.isna(s_sparse[m]):
                gap_streak += 1
                if gap_streak > max_gap_fill_months:
                    can_interpolate = False
                    break
            else:
                gap_streak = 0

        if can_interpolate:
            s_filled = s_sparse.interpolate(method="linear")
            filled_months = [str(m) for m in full_range if pd.isna(s_sparse[m])]
            if filled_months:
                flags.append(f"Linearly interpolated {len(filled_months)} missing month(s): {', '.join(filled_months[:4])}{'...' if len(filled_months)>4 else ''}")
            s_clean = s_filled
        else:
            flags.append(f"Series has gaps exceeding {max_gap_fill_months} months; using available points only")
            s_clean = pd.Series([month_dict[m] for m in months], index=pd.Index([str(m) for m in months]))
    else:
        s_clean = pd.Series([month_dict[m] for m in full_range], index=pd.Index([str(m) for m in full_range]))

    if (s_clean == 0.0).all():
        return None, flags + ["Series contains only zero postings; no usable demand signal"]

    # Ensure integer RangeIndex for statsmodels prediction compatibility
    s_clean_indexed = pd.Series(s_clean.values, index=pd.RangeIndex(len(s_clean)))
    return s_clean_indexed, flags


def forecast_demand_growth(
    cleaned_series: Optional[pd.Series],
    curated_trend: Optional[CuratedTrend],
    config: MarketSolverConfig = DEFAULT_CONFIG,
) -> Tuple[Optional[float], Optional[float], Optional[float], str, float, List[str]]:
    """Determine year-on-year demand growth bounds (g_low, g_central, g_high), method, and volatility.

    Method ladder:
    a) >= 24 points: statsmodels ETSModel (with seasonality if >= 36 points).
    b) 12-23 points: OLS on log(count + 1).
    c) < 12 points or fit failure: curated_trend fallback.
    d) None available: unavailable.
    """
    flags: List[str] = []

    if cleaned_series is None or len(cleaned_series) == 0:
        if curated_trend is not None:
            g_low, g_cen, g_high = curated_trend.growth_low, curated_trend.growth_central, curated_trend.growth_high
            volatility = max(0.0, (g_high - g_low) / 2.0)
            return g_low, g_cen, g_high, "curated_fallback", volatility, ["curated estimate, not forecast"]
        return None, None, None, "unavailable", 0.0, ["Demand trend unavailable"]

    n_points = len(cleaned_series)

    # Base level is mean of last 12 observed months
    if n_points >= 12:
        base = float(cleaned_series.iloc[-12:].mean())
    else:
        base = float(cleaned_series.mean())

    if base <= 0.0:
        if curated_trend is not None:
            g_low, g_cen, g_high = curated_trend.growth_low, curated_trend.growth_central, curated_trend.growth_high
            volatility = max(0.0, (g_high - g_low) / 2.0)
            return g_low, g_cen, g_high, "curated_fallback", volatility, ["Observed base postings zero; fell back to curated trend", "curated estimate, not forecast"]
        return None, None, None, "unavailable", 0.0, ["Observed base postings zero; trend unavailable"]

    # --- Method a: ETS (>= 24 points) ---
    if n_points >= config.min_points_ets:
        try:
            # Handle constant series directly
            if cleaned_series.nunique() == 1:
                g_cen = 0.0
                g_low = 0.0
                g_high = 0.0
                return g_low, g_cen, g_high, "constant_series", 0.0, ["Constant historical postings detected (zero growth variance)"]

            seasonal = "add" if n_points >= config.min_points_seasonal else None
            seasonal_periods = 12 if seasonal else None

            # Pass series with pd.RangeIndex so get_prediction has .index attribute
            ts_input = pd.Series(cleaned_series.values, index=pd.RangeIndex(n_points), dtype=float)

            model = ETSModel(
                ts_input,
                error="add",
                trend="add",
                damped_trend=True,
                seasonal=seasonal,
                seasonal_periods=seasonal_periods,
            )
            res = model.fit(disp=False)
            pred = res.get_prediction(start=n_points, end=n_points + config.forecast_horizon_months - 1)
            alpha = 1.0 - config.prediction_interval_level
            frame = pred.summary_frame(alpha=alpha)

            fut_mean = np.maximum(0.0, frame["mean"].values)
            fut_lower = np.maximum(0.0, frame["pi_lower"].values)
            fut_upper = np.maximum(0.0, frame["pi_upper"].values)

            mean_future = float(np.mean(fut_mean))
            lower_future = float(np.mean(fut_lower))
            upper_future = float(np.mean(fut_upper))

            g_cen = (mean_future / base) - 1.0
            g_low = (lower_future / base) - 1.0
            g_high = (upper_future / base) - 1.0

            method_name = "ETS(add, damped, seasonal)" if seasonal else "ETS(add, damped)"

            if not (g_low <= g_cen <= g_high):
                sorted_gs = sorted([g_low, g_cen, g_high])
                g_low, g_cen, g_high = sorted_gs[0], sorted_gs[1], sorted_gs[2]
                flags.append("Numerical order anomaly in ETS forecast; sorted intervals")

            volatility = max(0.0, (g_high - g_low) / 2.0)
            return g_low, g_cen, g_high, method_name, volatility, flags

        except Exception as exc:
            flags.append(f"ETS model fitting failed ({type(exc).__name__}); cascading down ladder")

    # --- Method b: OLS on log(count + 1) (12 to 23 points, or ETS failure) ---
    if n_points >= config.min_points_ols:
        try:
            if cleaned_series.nunique() == 1:
                g_cen = 0.0
                g_low = 0.0
                g_high = 0.0
                return g_low, g_cen, g_high, "constant_series", 0.0, ["Constant historical postings detected", "short series"]

            x = np.arange(n_points)
            y = np.log(cleaned_series.values + 1.0)
            X = sm.add_constant(x)
            mod = sm.OLS(y, X).fit()

            x_fut = np.arange(n_points, n_points + config.forecast_horizon_months)
            X_fut = sm.add_constant(x_fut)
            pred = mod.get_prediction(X_fut)
            alpha = 1.0 - config.prediction_interval_level
            frame = pred.summary_frame(alpha=alpha)

            fut_mean = np.maximum(0.0, np.exp(frame["mean"].values) - 1.0)
            fut_lower = np.maximum(0.0, np.exp(frame["obs_ci_lower"].values) - 1.0)
            fut_upper = np.maximum(0.0, np.exp(frame["obs_ci_upper"].values) - 1.0)

            mean_future = float(np.mean(fut_mean))
            lower_future = float(np.mean(fut_lower))
            upper_future = float(np.mean(fut_upper))

            g_cen = (mean_future / base) - 1.0
            g_low = (lower_future / base) - 1.0
            g_high = (upper_future / base) - 1.0

            flags.append("short series")

            if not (g_low <= g_cen <= g_high):
                sorted_gs = sorted([g_low, g_cen, g_high])
                g_low, g_cen, g_high = sorted_gs[0], sorted_gs[1], sorted_gs[2]
                flags.append("Numerical order anomaly in OLS forecast; sorted intervals")

            volatility = max(0.0, (g_high - g_low) / 2.0)
            return g_low, g_cen, g_high, "OLS(log-linear)", volatility, flags

        except Exception as exc:
            flags.append(f"OLS model fitting failed ({type(exc).__name__}); cascading down ladder")

    # --- Method c: Curated trend fallback (< 12 points or failures) ---
    if curated_trend is not None:
        g_low, g_cen, g_high = curated_trend.growth_low, curated_trend.growth_central, curated_trend.growth_high
        volatility = max(0.0, (g_high - g_low) / 2.0)
        flags.append("curated estimate, not forecast")
        return g_low, g_cen, g_high, "curated_fallback", volatility, flags

    # --- Method d: Nothing available ---
    flags.append("Demand trend unavailable")
    return None, None, None, "unavailable", 0.0, flags
