"""Normalization, filtering, and completeness calculations for Kp data."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from spaceweather.data_sources.base import KP_COLUMNS
from spaceweather.logging_config import get_logger

logger = get_logger("cleaning")

KP_CADENCE_HOURS = 3.0


def normalize_kp_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a canonical, UTC-sorted, deduplicated Kp frame.

    Invalid values are preserved as missing. Nothing is interpolated or zero-filled.
    """
    if frame.empty:
        return pd.DataFrame(columns=KP_COLUMNS)
    result = frame.copy()
    if "time_utc" not in result:
        raise ValueError("Kp frame is missing the time_utc column")
    result["time_utc"] = pd.to_datetime(result["time_utc"], utc=True, errors="coerce")
    result = result.loc[result["time_utc"].notna()]

    if "kp" not in result:
        result["kp"] = float("nan")
    result["kp"] = pd.to_numeric(result["kp"], errors="coerce")
    out_of_range = result["kp"].notna() & (
        (result["kp"] < 0.0) | (result["kp"] > 9.0)
    )
    if int(out_of_range.sum()):
        logger.warning("Masked %d Kp values outside 0-9", int(out_of_range.sum()))
        result.loc[out_of_range, "kp"] = float("nan")

    for column, dtype in (
        ("a_running", "Int64"),
        ("station_count", "Int64"),
    ):
        if column not in result:
            result[column] = pd.array([pd.NA] * len(result), dtype=dtype)
        result[column] = pd.array(
            pd.to_numeric(result[column], errors="coerce"), dtype=dtype
        )
    if "source" not in result:
        result["source"] = "unknown"
    if "status" not in result:
        result["status"] = "unknown"
    result["source"] = result["source"].fillna("unknown").astype(str)
    result["status"] = result["status"].fillna("unknown").astype(str)

    result["is_missing"] = (
        result.get("is_missing", pd.Series(False, index=result.index))
        .fillna(False)
        .astype(bool)
        | result["kp"].isna()
    )
    result = (
        result.sort_values("time_utc")
        .drop_duplicates("time_utc", keep="last")
        .reset_index(drop=True)
    )
    attrs = dict(frame.attrs)
    result.attrs.update(attrs)
    return result[KP_COLUMNS]


def filter_time_range(
    frame: pd.DataFrame,
    start: datetime | pd.Timestamp | None,
    end: datetime | pd.Timestamp | None,
    *,
    inclusive: bool = True,
) -> pd.DataFrame:
    """Filter a frame to a UTC window, returning a copy."""
    if frame.empty:
        return frame.copy()
    result = frame.copy()
    times = pd.to_datetime(result["time_utc"], utc=True, errors="coerce")
    result = result.assign(time_utc=times).loc[lambda df: df["time_utc"].notna()]
    if start is not None:
        start_ts = pd.Timestamp(start)
        if start_ts.tzinfo is None:
            start_ts = start_ts.tz_localize("UTC")
        result = result.loc[result["time_utc"] >= start_ts]
    if end is not None:
        end_ts = pd.Timestamp(end)
        if end_ts.tzinfo is None:
            end_ts = end_ts.tz_localize("UTC")
        result = result.loc[result["time_utc"] <= end_ts] if inclusive else result.loc[
            result["time_utc"] < end_ts
        ]
    return result.sort_values("time_utc").reset_index(drop=True)


def valid_kp(frame: pd.DataFrame) -> pd.DataFrame:
    """Return rows with a usable Kp value."""
    if frame.empty:
        return frame.copy()
    return frame.loc[frame["kp"].notna() & ~frame["is_missing"]].copy()


def expected_kp_samples(
    start: datetime | pd.Timestamp,
    end: datetime | pd.Timestamp,
    *,
    cadence_hours: float = KP_CADENCE_HOURS,
) -> int:
    """Number of three-hour slots expected in an inclusive window."""
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    seconds = (end_ts - start_ts).total_seconds()
    if seconds < 0:
        return 0
    return int(seconds // (cadence_hours * 3600)) + 1


def data_completeness(
    frame: pd.DataFrame,
    *,
    start: datetime | pd.Timestamp | None = None,
    end: datetime | pd.Timestamp | None = None,
    cadence_hours: float = KP_CADENCE_HOURS,
) -> float:
    """Fraction of expected slots that contain a valid observation (0-1)."""
    valid = valid_kp(frame)
    if valid.empty:
        return 0.0
    window_start = pd.Timestamp(start) if start is not None else valid["time_utc"].min()
    window_end = pd.Timestamp(end) if end is not None else valid["time_utc"].max()
    expected = expected_kp_samples(window_start, window_end, cadence_hours=cadence_hours)
    if expected <= 0:
        return 0.0
    return float(min(len(valid) / expected, 1.0))


def merge_kp_sources(
    recent: pd.DataFrame, historical: pd.DataFrame
) -> pd.DataFrame:
    """Combine sources, preferring the most recently retrieved duplicate slots."""
    frames = [frame for frame in (historical, recent) if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=KP_COLUMNS)
    combined = pd.concat(frames, ignore_index=True)
    normalized = normalize_kp_frame(combined)
    normalized.attrs["issues"] = list(historical.attrs.get("issues", [])) + list(
        recent.attrs.get("issues", [])
    )
    return normalized


def missing_summary(
    frame: pd.DataFrame,
    *,
    start: datetime | pd.Timestamp | None = None,
    end: datetime | pd.Timestamp | None = None,
) -> dict[str, float | int]:
    """Summarize counts of valid, flagged-missing, and expected observations."""
    valid = valid_kp(frame)
    total = len(frame)
    missing = int(total - len(valid))
    expected = (
        expected_kp_samples(start, end)
        if start is not None and end is not None
        else total
    )
    return {
        "total_rows": total,
        "valid_rows": len(valid),
        "missing_rows": missing,
        "expected_slots": expected,
        "completeness": data_completeness(frame, start=start, end=end),
    }
