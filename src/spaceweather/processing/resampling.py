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


def downsample_for_display(frame: pd.DataFrame, *, max_points: int = 5000) -> pd.DataFrame:
    """Uniformly subsample a long series, recording the disclosure in ``attrs``."""
    if len(frame) <= max_points or max_points < 2:
        return frame.copy()
    stride = math.ceil(len(frame) / max_points)
    result = frame.iloc[::stride].copy()
    result.attrs.update(frame.attrs)
    result.attrs["downsample_note"] = (
        f"Display downsampled by taking every {stride}th observation "
        f"({len(result)} of {len(frame)} rows). Downloads retain all rows."
    )
    logger.info(result.attrs["downsample_note"])
    return result
