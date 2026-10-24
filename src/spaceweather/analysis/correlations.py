"""Correlation, lag, and uncertainty calculations with explicit caveats."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

from spaceweather.exceptions import InsufficientDataError
from spaceweather.logging_config import get_logger

logger = get_logger("correlations")


def _clean_pairs(x: pd.Series, y: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "x": pd.to_numeric(x, errors="coerce"),
            "y": pd.to_numeric(y, errors="coerce"),
        }
    ).dropna()


def _fisher_ci(r: float, n: int, *, confidence: float = 0.95) -> tuple[float, float]:
    if n <= 3 or not math.isfinite(r) or abs(r) >= 1.0:
        return (float("nan"), float("nan"))
    z = np.arctanh(r)
    se = 1.0 / math.sqrt(n - 3)
    critical = stats.norm.ppf(0.5 + confidence / 2.0)
    return (float(np.tanh(z - critical * se)), float(np.tanh(z + critical * se)))


def _lag1_autocorrelation(series: pd.Series) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if len(clean) < 3:
        return 0.0
    value = clean.autocorr(lag=1)
    return 0.0 if value is None or not math.isfinite(float(value)) else float(value)


def effective_sample_size(x: pd.Series, y: pd.Series) -> float:
    """Approximate independent sample size from lag-1 autocorrelation.

    This is a conservative diagnostic for serially correlated geophysical series,
    not a replacement for a dedicated time-series model.
    """
    frame = _clean_pairs(x, y)
    n = len(frame)
    if n < 4:
        return float(n)
    r1x = _lag1_autocorrelation(frame["x"])
    r1y = _lag1_autocorrelation(frame["y"])
    product = r1x * r1y
    denominator = 1.0 + product
    if denominator <= 0:
        return float(n)
    estimate = n * (1.0 - product) / denominator
    return float(min(max(estimate, 3.0), n))


def correlate(x: pd.Series, y: pd.Series) -> dict[str, float | int]:
    """Pearson and Spearman correlation with naive and autocorrelation-aware CIs."""
    frame = _clean_pairs(x, y)
    n = len(frame)
    if n < 3:
        raise InsufficientDataError(
            f"At least 3 paired observations are required; received {n}."
        )
    pearson = stats.pearsonr(frame["x"], frame["y"])
    spearman = stats.spearmanr(frame["x"], frame["y"])
    n_effective = effective_sample_size(frame["x"], frame["y"])
    naive_ci = _fisher_ci(float(pearson.statistic), n)
    effective_ci = _fisher_ci(float(pearson.statistic), round(n_effective))
    return {
        "n": n,
        "n_effective": n_effective,
        "pearson_r": float(pearson.statistic),
        "pearson_p": float(pearson.pvalue),
        "pearson_ci95_naive_low": naive_ci[0],
        "pearson_ci95_naive_high": naive_ci[1],
        "pearson_ci95_effective_low": effective_ci[0],
        "pearson_ci95_effective_high": effective_ci[1],
        "spearman_rho": float(spearman.statistic),
        "spearman_p": float(spearman.pvalue),
    }


def lagged_cross_correlation(
    frame: pd.DataFrame,
    *,
    x: str,
    y: str,
    max_lag_hours: float = 12.0,
    step_hours: float = 3.0,
) -> pd.DataFrame:
    """Compute correlation of ``x(t)`` with ``y(t + lag)`` over a lag grid.

    Positive lags mean that ``x`` leads ``y``. The input must already be on a
    regular grid; rows with missing values are excluded pairwise.
    """
    if frame.empty:
        raise InsufficientDataError("Cannot compute lag correlation on an empty frame")
    if step_hours <= 0:
        raise ValueError("step_hours must be positive")
    if max_lag_hours < 0:
        raise ValueError("max_lag_hours must be non-negative")
    if max_lag_hours % step_hours != 0:
        raise ValueError("max_lag_hours must be a multiple of step_hours")
    required = {"time_utc", x, y}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing columns for lag analysis: {sorted(missing)}")

    working = frame[["time_utc", x, y]].copy()
    working["time_utc"] = pd.to_datetime(working["time_utc"], utc=True, errors="coerce")
    working = working.dropna(subset=["time_utc"]).sort_values("time_utc")
    working = working.drop_duplicates("time_utc", keep="last").set_index("time_utc")
    steps = round(max_lag_hours / step_hours)
    records: list[dict[str, float | int]] = []
    for lag_step in range(-steps, steps + 1):
        paired = pd.DataFrame(
            {
                "x": pd.to_numeric(working[x], errors="coerce"),
                "y": pd.to_numeric(working[y], errors="coerce").shift(-lag_step),
            }
        ).dropna()
        if len(paired) < 3:
            continue
        result = stats.pearsonr(paired["x"], paired["y"])
        records.append(
            {
                "lag_hours": lag_step * step_hours,
                "r": float(result.statistic),
                "p_value": float(result.pvalue),
                "n": len(paired),
            }
        )
    return pd.DataFrame.from_records(records)


def rolling_correlation(
    frame: pd.DataFrame,
    *,
    x: str,
    y: str,
    window: int = 30,
) -> pd.Series:
    """Rolling Pearson correlation on an aligned frame."""
    if window < 3:
        raise ValueError("window must be at least 3")
    return frame[x].rolling(window, min_periods=window).corr(frame[y])
