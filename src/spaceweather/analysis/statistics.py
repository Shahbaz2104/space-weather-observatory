"""Descriptive metrics and automatically generated data summaries."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from spaceweather.models import SourceInfo
from spaceweather.processing.cleaning import data_completeness, valid_kp
from spaceweather.processing.events import detect_events, kp_to_g_scale


def summary_metrics(
    frame: pd.DataFrame,
    *,
    threshold: float = 5.0,
    start: datetime | pd.Timestamp | None = None,
    end: datetime | pd.Timestamp | None = None,
) -> dict[str, object]:
    """Compute the headline metrics shown on the overview page."""
    valid = valid_kp(frame)
    latest_time: datetime | None = None
    latest_kp: float | None = None
    latest_status: str | None = None
    if not valid.empty:
        row = valid.iloc[-1]
        latest_time = pd.Timestamp(row["time_utc"]).to_pydatetime()
        latest_kp = float(row["kp"])
        latest_status = str(row["status"])

    peak_kp = float(valid["kp"].max()) if not valid.empty else None
    peak_time = (
        pd.Timestamp(valid.loc[valid["kp"].idxmax(), "time_utc"]).to_pydatetime()
        if not valid.empty
        else None
    )
    storm_samples = int((valid["kp"] >= threshold).sum())
    storm_pct = (storm_samples / len(valid) * 100.0) if len(valid) else 0.0
    events = detect_events(frame, threshold=threshold)
    longest = max((event.duration_hours for event in events), default=0.0)

    source = frame.attrs.get("source_info")
    last_updated = source.retrieved_at if isinstance(source, SourceInfo) else None

    window_start = (
        pd.Timestamp(start).to_pydatetime()
        if start is not None
        else (pd.Timestamp(valid["time_utc"].min()).to_pydatetime() if not valid.empty else None)
    )
    window_end = (
        pd.Timestamp(end).to_pydatetime()
        if end is not None
        else (pd.Timestamp(valid["time_utc"].max()).to_pydatetime() if not valid.empty else None)
    )

    return {
        "latest_time": latest_time,
        "latest_kp": latest_kp,
        "latest_status": latest_status,
        "latest_g_scale": kp_to_g_scale(latest_kp) if latest_kp is not None else None,
        "peak_kp": peak_kp,
        "peak_time": peak_time,
        "peak_g_scale": kp_to_g_scale(peak_kp) if peak_kp is not None else None,
        "storm_samples": storm_samples,
        "storm_pct": storm_pct,
        "valid_samples": len(valid),
        "event_count": len(events),
        "longest_event_hours": longest,
        "completeness": data_completeness(
            frame, start=window_start, end=window_end
        ),
        "last_updated": last_updated,
        "window_start": window_start,
        "window_end": window_end,
        "threshold": threshold,
    }


def auto_summary(
    frame: pd.DataFrame,
    *,
    threshold: float = 5.0,
    start: datetime | pd.Timestamp | None = None,
    end: datetime | pd.Timestamp | None = None,
) -> list[str]:
    """Generate plain-language statements strictly from the selected data."""
    metrics = summary_metrics(frame, threshold=threshold, start=start, end=end)
    if metrics["valid_samples"] == 0:
        return ["No valid Kp observations are available for the selected window."]

    start_text = pd.Timestamp(metrics["window_start"]).strftime("%Y-%m-%d %H:%M UTC")
    end_text = pd.Timestamp(metrics["window_end"]).strftime("%Y-%m-%d %H:%M UTC")
    statements = [
        (
            f"Between {start_text} and {end_text}, the selection contains "
            f"{metrics['valid_samples']} valid three-hour Kp observations "
            f"({metrics['completeness']:.0%} of expected slots)."
        )
    ]
    if metrics["latest_kp"] is not None:
        g_text = (
            f", corresponding to {metrics['latest_g_scale']}"
            if metrics["latest_g_scale"]
            else ""
        )
        statements.append(
            f"The latest available observation is Kp {metrics['latest_kp']:.2f} "
            f"at {pd.Timestamp(metrics['latest_time']).strftime('%Y-%m-%d %H:%M UTC')} "
            f"({metrics['latest_status']}{g_text})."
        )
    if metrics["peak_kp"] is not None:
        peak_g = (
            f" ({metrics['peak_g_scale']})" if metrics["peak_g_scale"] else ""
        )
        statements.append(
            f"Peak observed Kp is {metrics['peak_kp']:.2f}{peak_g} at "
            f"{pd.Timestamp(metrics['peak_time']).strftime('%Y-%m-%d %H:%M UTC')}."
        )
    statements.append(
        f"{metrics['storm_samples']} observations ({metrics['storm_pct']:.1f}% of valid "
        f"samples) meet or exceed the Kp {threshold:g} threshold; "
        f"{metrics['event_count']} contiguous storm-level run(s) were detected."
    )
    statements.append(
        "These are descriptive statistics for the selected observations; they do not "
        "establish a physical cause or an operational forecast."
    )
    return statements


def rolling_mean(series: pd.Series, window: int = 8) -> pd.Series:
    """Rolling mean that preserves missing observations as missing."""
    if window < 1:
        raise ValueError("window must be positive")
    return series.rolling(window, min_periods=max(2, window // 2)).mean()


def distribution_summary(series: pd.Series) -> dict[str, float]:
    """Basic descriptive statistics for a numeric series."""
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {
            "n": 0.0,
            "mean": float("nan"),
            "median": float("nan"),
            "std": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
        }
    return {
        "n": float(len(clean)),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "std": float(clean.std(ddof=1)) if len(clean) > 1 else 0.0,
        "min": float(clean.min()),
        "max": float(clean.max()),
    }
