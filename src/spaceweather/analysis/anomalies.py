"""Simple, transparent anomaly diagnostics for geomagnetic series."""

from __future__ import annotations

import pandas as pd


def robust_zscore(series: pd.Series) -> pd.Series:
    """Median/MAD z-score that is resistant to extreme geomagnetic values."""
    clean = pd.to_numeric(series, errors="coerce")
    median = clean.median()
    deviation = (clean - median).abs()
    mad = deviation.median()
    if mad == 0 or pd.isna(mad):
        std = clean.std(ddof=1)
        if not std or pd.isna(std):
            return pd.Series(float("nan"), index=series.index)
        return (clean - clean.mean()) / std
    return 0.6745 * (clean - median) / mad


def flag_anomalies(
    frame: pd.DataFrame,
    *,
    value_column: str = "kp",
    z_threshold: float = 3.5,
) -> pd.DataFrame:
    """Return a copy with ``z_score`` and ``is_anomaly`` columns.

    Anomalies are statistical deviations from the selected window's median; they
    are not event classifications.
    """
    if value_column not in frame:
        raise ValueError(f"Column {value_column!r} is not present")
    result = frame.copy()
    result["z_score"] = robust_zscore(result[value_column])
    result["is_anomaly"] = result["z_score"].abs() >= z_threshold
    return result
