"""Correlation, effective sample size, and lag-direction tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spaceweather.analysis.correlations import (
    correlate,
    effective_sample_size,
    lagged_cross_correlation,
)
from spaceweather.exceptions import InsufficientDataError


def test_correlation_and_bounds() -> None:
    rng = np.random.default_rng(11)
    x = pd.Series(rng.normal(size=30))
    y = 2.0 * x + rng.normal(scale=2.0, size=30)
    result = correlate(x, y)
    assert result["n"] == 30
    assert 0.0 < result["pearson_r"] < 1.0
    assert 3.0 <= result["n_effective"] <= 30.0
    assert result["pearson_ci95_effective_low"] <= result["pearson_r"]
    assert result["pearson_ci95_effective_high"] >= result["pearson_r"]


def test_perfect_correlation_has_undefined_fisher_interval() -> None:
    x = pd.Series(np.arange(1.0, 21.0))
    result = correlate(x, 2.0 * x + 1.0)
    assert result["pearson_r"] == pytest.approx(1.0)
    assert np.isnan(result["pearson_ci95_effective_low"])


def test_negative_association() -> None:
    x = pd.Series(np.linspace(0.0, 10.0, 15))
    y = -x
    result = correlate(x, y)
    assert result["pearson_r"] == pytest.approx(-1.0)
    assert result["spearman_rho"] == pytest.approx(-1.0)


def test_missing_pairs_are_dropped() -> None:
    x = pd.Series([1.0, 2.0, None, 4.0, 5.0])
    y = pd.Series([2.0, None, 6.0, 8.0, 10.0])
    result = correlate(x, y)
    assert result["n"] == 3


def test_too_few_pairs_raise() -> None:
    with pytest.raises(InsufficientDataError):
        correlate(pd.Series([1.0, 2.0]), pd.Series([2.0, 4.0]))


def test_effective_sample_size_is_bounded() -> None:
    rng = np.random.default_rng(7)
    x = pd.Series(rng.normal(size=200))
    y = pd.Series(rng.normal(size=200))
    n_eff = effective_sample_size(x, y)
    assert 3.0 <= n_eff <= len(x)


def test_positive_lag_means_x_leads_y() -> None:
    times = pd.date_range("2024-01-01", periods=40, freq="3h", tz="UTC")
    rng = np.random.default_rng(42)
    x = rng.normal(size=len(times))
    y = np.concatenate([[np.nan], x[:-1]])
    frame = pd.DataFrame({"time_utc": times, "x": x, "y": y})
    lag = lagged_cross_correlation(
        frame, x="x", y="y", max_lag_hours=9.0, step_hours=3.0
    )
    strongest = lag.loc[lag["r"].abs().idxmax()]
    assert strongest["lag_hours"] == 3.0
    assert strongest["r"] == pytest.approx(1.0)


def test_lag_rejects_invalid_grid() -> None:
    frame = pd.DataFrame(
        {
            "time_utc": pd.date_range("2024-01-01", periods=5, freq="3h", tz="UTC"),
            "x": range(5),
            "y": range(5),
        }
    )
    with pytest.raises(ValueError):
        lagged_cross_correlation(frame, x="x", y="y", max_lag_hours=5.0)
