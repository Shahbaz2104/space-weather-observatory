"""Shared column definitions and helpers for source adapters."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from spaceweather.models import Attribution, DataStatus, SourceInfo

KP_COLUMNS = [
    "time_utc",
    "kp",
    "a_running",
    "station_count",
    "source",
    "status",
    "is_missing",
]

SOLAR_WIND_COLUMNS = [
    "time_utc",
    "speed_kms",
    "density_cm3",
    "temperature_k",
    "bz_gsm_nt",
    "bt_nt",
    "source",
    "status",
    "is_missing",
]


def empty_kp_frame() -> pd.DataFrame:
    """Return an empty Kp frame with the canonical columns and dtypes."""
    frame = pd.DataFrame(
        {
            "time_utc": pd.Series(dtype="datetime64[ns, UTC]"),
            "kp": pd.Series(dtype="float64"),
            "a_running": pd.Series(dtype="Int64"),
            "station_count": pd.Series(dtype="Int64"),
            "source": pd.Series(dtype="object"),
            "status": pd.Series(dtype="object"),
            "is_missing": pd.Series(dtype="bool"),
        }
    )
    return frame[KP_COLUMNS]


def empty_solar_wind_frame() -> pd.DataFrame:
    """Return an empty solar-wind frame with the canonical columns and dtypes."""
    frame = pd.DataFrame(
        {
            "time_utc": pd.Series(dtype="datetime64[ns, UTC]"),
            "speed_kms": pd.Series(dtype="float64"),
            "density_cm3": pd.Series(dtype="float64"),
            "temperature_k": pd.Series(dtype="float64"),
            "bz_gsm_nt": pd.Series(dtype="float64"),
            "bt_nt": pd.Series(dtype="float64"),
            "source": pd.Series(dtype="object"),
            "status": pd.Series(dtype="object"),
            "is_missing": pd.Series(dtype="bool"),
        }
    )
    return frame[SOLAR_WIND_COLUMNS]


def make_source_info(
    attribution: Attribution,
    *,
    retrieved_at: datetime | None,
    stale: bool,
    from_cache: bool,
    status: DataStatus,
    url: str | None = None,
) -> SourceInfo:
    """Build runtime source metadata from a static attribution entry."""
    return SourceInfo(
        key=attribution.key,
        name=attribution.name,
        url=url or attribution.url,
        license=attribution.license,
        citation=attribution.citation,
        retrieved_at=retrieved_at,
        stale=stale,
        from_cache=from_cache,
        status=status,
    )


def attach_attrs(
    frame: pd.DataFrame,
    *,
    source_info: SourceInfo,
    units: dict[str, str],
    issues: list[str] | None = None,
) -> pd.DataFrame:
    """Attach provenance metadata to a dataframe without altering its data."""
    result = frame.copy()
    result.attrs["source_info"] = source_info
    result.attrs["units"] = units
    result.attrs["issues"] = list(issues or [])
    return result
