"""Explicit cadence alignment and display downsampling."""

from __future__ import annotations

import math
from collections.abc import Iterable

import pandas as pd

from spaceweather.logging_config import get_logger

logger = get_logger("resampling")


def infer_cadence_minutes(frame: pd.DataFrame) -> float | None:
    """Infer the median sampling interval in minutes."""
    if frame.empty or "time_utc" not in frame:
        return None
    times = pd.to_datetime(frame["time_utc"], utc=True, errors="coerce").dropna().sort_values()
    if len(times) < 2:
        return None
    diffs = times.diff().dropna().dt.total_seconds() / 60.0
    if diffs.empty:
        return None
    return float(diffs.median())


def aggregate_solar_wind(
    frame: pd.DataFrame,
    *,
    value_columns: Iterable[str] = ("speed_kms", "density_cm3", "bz_gsm_nt", "bt_nt"),
    freq: str = "3h",
) -> pd.DataFrame:
    """Aggregate solar-wind measurements onto fixed left-labelled bins.

    The returned frame includes the number of contributing samples and the
    coverage fraction for each bin. Missing bins stay absent rather than zero.
    """
    if frame.empty:
        return pd.DataFrame(columns=["time_utc", "n_samples", "coverage_fraction"])
    working = frame.copy()
    working["time_utc"] = pd.to_datetime(working["time_utc"], utc=True, errors="coerce")
    working = working.loc[working["time_utc"].notna()].set_index("time_utc")
    columns = [column for column in value_columns if column in working.columns]
    if not columns:
        raise ValueError("No requested solar-wind value columns are present")

    grouped = working[columns].resample(freq, label="left", closed="left")
    means = grouped.mean()
    counts = grouped.count()
    n_samples = counts[columns[0]].astype(int)
    cadence_minutes = infer_cadence_minutes(frame)
    bin_minutes = pd.Timedelta(freq).total_seconds() / 60.0
    expected = (
        max(1.0, bin_minutes / cadence_minutes) if cadence_minutes else float("nan")
    )
    result = means.reset_index()
    result["n_samples"] = n_samples.to_numpy()
    result["coverage_fraction"] = (
        (result["n_samples"] / expected).clip(upper=1.0) if cadence_minutes else 1.0
    )
    return result


def align_solar_wind_with_kp(
    solar_wind: pd.DataFrame,
    kp: pd.DataFrame,
    *,
    freq: str = "3h",
) -> pd.DataFrame:
    """Inner-join binned solar wind with Kp observations on the same UTC grid.

    Both series are aggregated on the same left-labelled three-hour bins, which
    matches how Kp timestamps represent the start of a three-hour interval.
    """
    if solar_wind.empty or kp.empty:
        return pd.DataFrame()
    aggregated = aggregate_solar_wind(solar_wind, freq=freq)
    kp_working = kp.copy()
    kp_working["time_utc"] = pd.to_datetime(
        kp_working["time_utc"], utc=True, errors="coerce"
    )
    kp_working = kp_working.loc[kp_working["time_utc"].notna()]
    kp_working = kp_working.rename(
        columns={"status": "kp_status", "source": "kp_source"}
    )
    keep = [
        "time_utc",
        "kp",
        "kp_status",
        "kp_source",
        "ap",
    ]
    keep = [column for column in keep if column in kp_working.columns]
    merged = pd.merge(
        aggregated,
        kp_working[keep],
        on="time_utc",
        how="inner",
        validate="one_to_one",
    )
    merged["solar_wind_source"] = (
        solar_wind["source"].dropna().iloc[0]
        if "source" in solar_wind.columns and not solar_wind["source"].dropna().empty
        else "unknown"
    )
    return merged.sort_values("time_utc").reset_index(drop=True)


def downsample_for_display(
    frame: pd.DataFrame,
    *,
    max_points: int = 5000,
    value_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Uniformly subsample a long series for rendering, recording the disclosure.

    Endpoints and the boundaries of missing-data runs are retained so a gap is never
    visually bridged. Metrics, event detection, tables, and exports must use the
    original frame; only chart traces should receive this result.
    """
    total = len(frame)
    if total <= max_points or max_points < 3:
        return frame.copy()

    stride = math.ceil(total / max_points)
    keep = set(range(0, total, stride))
    boundaries = {0, total - 1}

    if value_columns is not None:
        columns = [column for column in value_columns if column in frame.columns]
        missing = (
            frame.loc[:, columns].isna().all(axis=1).to_numpy()
            if columns
            else frame.isna().any(axis=1).to_numpy()
        )
    else:
        missing = frame.isna().any(axis=1).to_numpy()

    run_start: int | None = None
    for position, is_missing in enumerate(missing):
        if is_missing and run_start is None:
            run_start = position
        elif not is_missing and run_start is not None:
            for index in (run_start - 1, run_start, position - 1, position):
                if 0 <= index < total:
                    boundaries.add(index)
            run_start = None
    if run_start is not None:
        for index in (run_start - 1, run_start, total - 1):
            if 0 <= index < total:
                boundaries.add(index)

    keep.update(boundaries)
    if len(keep) > max_points:
        available = max(1, max_points - len(boundaries))
        stride = max(stride, math.ceil(total / available))
        keep = set(range(0, total, stride)) | boundaries

    result = frame.iloc[sorted(keep)].copy()
    result.attrs.update(frame.attrs)
    result.attrs["downsample_stride"] = stride
    result.attrs["downsample_rows_total"] = total
    result.attrs["downsample_rows_displayed"] = len(result)
    result.attrs["downsample_note"] = (
        f"Display downsampled by taking every {stride}th observation plus endpoint "
        f"and missing-gap boundaries ({len(result):,} of {total:,} rows). "
        "Metrics, detected events, and downloads retain every row."
    )
    logger.info(result.attrs["downsample_note"])
    return result


def display_sampling_metadata(frame: pd.DataFrame) -> dict[str, object]:
    """Return the render-time sampling disclosure stored on a frame, if any."""
    note = frame.attrs.get("downsample_note")
    if not note:
        return {}
    return {
        "downsample_note": str(note),
        "downsample_stride": int(frame.attrs.get("downsample_stride", 1)),
        "downsample_rows_total": int(frame.attrs.get("downsample_rows_total", len(frame))),
        "downsample_rows_displayed": int(
            frame.attrs.get("downsample_rows_displayed", len(frame))
        ),
    }
