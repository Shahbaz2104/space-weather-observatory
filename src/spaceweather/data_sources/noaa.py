"""NOAA SWPC adapters for planetary Kp and solar-wind products."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from spaceweather.attribution import NOAA_SWPC
from spaceweather.config import Settings
from spaceweather.data_sources.base import (
    KP_COLUMNS,
    SOLAR_WIND_COLUMNS,
    attach_attrs,
    make_source_info,
)
from spaceweather.exceptions import SchemaValidationError, SourceError
from spaceweather.ingestion.fetch import HttpClient
from spaceweather.ingestion.validate import (
    coerce_kp,
    mask_fill_values,
    parse_table,
    require_columns,
    to_utc_series,
)
from spaceweather.logging_config import get_logger
from spaceweather.models import DataStatus, SourceInfo, ValidationIssue

logger = get_logger("noaa")

KP_UNITS = {"kp": "unitless (0-9)", "a_running": "nT (derived amplitude)", "station_count": "stations"}
SOLAR_WIND_UNITS = {
    "speed_kms": "km/s",
    "density_cm3": "protons/cm^3",
    "temperature_k": "K",
    "bz_gsm_nt": "nT (GSM)",
    "bt_nt": "nT",
}


def parse_recent_kp(payload: object) -> tuple[pd.DataFrame, list[ValidationIssue]]:
    """Parse the NOAA observed planetary K-index JSON product."""
    records, parse_issues = parse_table(payload, source="NOAA planetary K-index")
    raw = pd.DataFrame.from_records(records)
    require_columns(raw, ["time_tag", "Kp"], source="NOAA planetary K-index")

    issues: list[ValidationIssue] = [
        ValidationIssue(level="warning", message=message) for message in parse_issues
    ]
    times = to_utc_series(raw["time_tag"])
    invalid_times = int(times.isna().sum())
    kp, invalid_kp = coerce_kp(raw["Kp"])
    if invalid_times:
        issues.append(
            ValidationIssue(
                level="warning",
                message="Rows with an unparseable timestamp were dropped.",
                count=invalid_times,
            )
        )
    if invalid_kp:
        issues.append(
            ValidationIssue(
                level="warning",
                message="Kp values outside 0-9 were treated as missing.",
                count=invalid_kp,
            )
        )

    def optional_int(column: str) -> pd.Series:
        if column not in raw.columns:
            return pd.array([pd.NA] * len(raw), dtype="Int64")
        return pd.array(pd.to_numeric(raw[column], errors="coerce"), dtype="Int64")

    frame = pd.DataFrame(
        {
            "time_utc": times,
            "kp": kp,
            "a_running": optional_int("a_running"),
            "station_count": optional_int("station_count"),
            "source": "NOAA SWPC",
            "status": DataStatus.PRELIMINARY.value,
            "is_missing": kp.isna(),
        }
    ).loc[lambda df: df["time_utc"].notna()]
    frame = frame.sort_values("time_utc").drop_duplicates("time_utc", keep="last")
    missing_count = int(frame["is_missing"].sum())
    if missing_count:
        issues.append(
            ValidationIssue(
                level="info",
                message="Observations with a missing Kp value were retained and flagged.",
                count=missing_count,
            )
        )
    return frame.reset_index(drop=True)[KP_COLUMNS], issues


def fetch_recent_kp(client: HttpClient, settings: Settings) -> tuple[pd.DataFrame, SourceInfo]:
    """Retrieve the most recent seven days of observed Kp."""
    result = client.fetch(settings.recent_kp_url, ttl_seconds=settings.recent_kp_ttl_seconds)
    frame, issues = parse_recent_kp(result.json())
    source = make_source_info(
        NOAA_SWPC,
        retrieved_at=result.retrieved_at,
        stale=result.stale,
        from_cache=result.from_cache,
        status=DataStatus.PRELIMINARY,
        url=result.url,
    )
    frame = attach_attrs(
        frame,
        source_info=source,
        units=KP_UNITS,
        issues=[issue.message for issue in issues],
    )
    logger.info(
        "Loaded %d NOAA Kp observations (%s to %s)",
        len(frame),
        frame["time_utc"].min(),
        frame["time_utc"].max(),
    )
    return frame, source


def parse_propagated_solar_wind(payload: object) -> tuple[pd.DataFrame, list[ValidationIssue]]:
    """Parse the SWPC seven-day propagated solar-wind product (one-minute cadence)."""
    records, parse_issues = parse_table(payload, source="NOAA propagated solar wind")
    raw = pd.DataFrame.from_records(records)
    required = ["time_tag", "speed", "density", "bz", "bt"]
    require_columns(raw, required, source="NOAA propagated solar wind")

    times = to_utc_series(raw["time_tag"])
    speed = mask_fill_values(raw["speed"], threshold=9999.0)
    density = mask_fill_values(raw["density"], threshold=999.0)
    bz = mask_fill_values(raw["bz"], threshold=999.0)
    bt = mask_fill_values(raw["bt"], threshold=999.0)
    temperature = (
        mask_fill_values(raw["temperature"], threshold=9_999_999.0)
        if "temperature" in raw.columns
        else pd.Series(float("nan"), index=raw.index)
    )

    frame = pd.DataFrame(
        {
            "time_utc": times,
            "speed_kms": speed,
            "density_cm3": density,
            "temperature_k": temperature,
            "bz_gsm_nt": bz,
            "bt_nt": bt,
            "source": "NOAA SWPC",
            "status": DataStatus.ESTIMATED.value,
        }
    ).loc[lambda df: df["time_utc"].notna()]
    frame["is_missing"] = frame[
        ["speed_kms", "density_cm3", "bz_gsm_nt", "bt_nt"]
    ].isna().all(axis=1)
    frame = frame.sort_values("time_utc").drop_duplicates("time_utc", keep="last")

    issues = [ValidationIssue(level="warning", message=message) for message in parse_issues]
    missing_count = int(frame["is_missing"].sum())
    if missing_count:
        issues.append(
            ValidationIssue(
                level="info",
                message="Rows with all solar-wind fields missing were retained and flagged.",
                count=missing_count,
            )
        )
    return frame.reset_index(drop=True)[SOLAR_WIND_COLUMNS], issues


def fetch_propagated_solar_wind(
    client: HttpClient, settings: Settings
) -> tuple[pd.DataFrame, SourceInfo]:
    """Retrieve seven days of one-minute propagated (modeled) solar wind."""
    result = client.fetch(
        settings.propagated_solar_wind_url, ttl_seconds=settings.recent_kp_ttl_seconds
    )
    frame, issues = parse_propagated_solar_wind(result.json())
    source = make_source_info(
        NOAA_SWPC,
        retrieved_at=result.retrieved_at,
        stale=result.stale,
        from_cache=result.from_cache,
        status=DataStatus.ESTIMATED,
        url=result.url,
    )
    frame = attach_attrs(
        frame,
        source_info=source,
        units=SOLAR_WIND_UNITS,
        issues=[issue.message for issue in issues],
    )
    return frame, source


def _parse_single_record(payload: object, source: str) -> dict[str, Any]:
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return dict(payload[-1])
    raise SchemaValidationError(f"{source}: expected a JSON array containing one object")


def fetch_solar_wind_snapshot(
    client: HttpClient, settings: Settings
) -> tuple[dict[str, object], list[SourceInfo], list[str]]:
    """Fetch the latest speed and magnetic-field values for status cards."""
    snapshot: dict[str, object] = {
        "speed_kms": None,
        "speed_time_utc": None,
        "bt_nt": None,
        "bz_gsm_nt": None,
        "mag_time_utc": None,
    }
    sources: list[SourceInfo] = []
    warnings: list[str] = []

    try:
        speed_result = client.fetch(settings.solar_wind_speed_url, ttl_seconds=300)
        speed = _parse_single_record(speed_result.json(), "NOAA solar-wind speed")
        snapshot["speed_kms"] = float(speed["proton_speed"])
        snapshot["speed_time_utc"] = pd.to_datetime(speed["time_tag"], utc=True).to_pydatetime()
        sources.append(
            make_source_info(
                NOAA_SWPC,
                retrieved_at=speed_result.retrieved_at,
                stale=speed_result.stale,
                from_cache=speed_result.from_cache,
                status=DataStatus.OBSERVED,
                url=speed_result.url,
            )
        )
    except (SourceError, KeyError, TypeError, ValueError) as exc:
        warnings.append(f"Latest solar-wind speed unavailable: {exc}")

    try:
        mag_result = client.fetch(settings.solar_wind_mag_url, ttl_seconds=300)
        mag = _parse_single_record(mag_result.json(), "NOAA solar-wind magnetic field")
        snapshot["bt_nt"] = float(mag["bt"])
        snapshot["bz_gsm_nt"] = float(mag["bz_gsm"])
        snapshot["mag_time_utc"] = pd.to_datetime(mag["time_tag"], utc=True).to_pydatetime()
        sources.append(
            make_source_info(
                NOAA_SWPC,
                retrieved_at=mag_result.retrieved_at,
                stale=mag_result.stale,
                from_cache=mag_result.from_cache,
                status=DataStatus.OBSERVED,
                url=mag_result.url,
            )
        )
    except (SourceError, KeyError, TypeError, ValueError) as exc:
        warnings.append(f"Latest solar-wind magnetic field unavailable: {exc}")

    return snapshot, sources, warnings


def latest_observation(frame: pd.DataFrame) -> tuple[datetime | None, float | None]:
    """Return the latest valid Kp observation, or ``(None, None)``."""
    if frame.empty:
        return None, None
    valid = frame.loc[~frame["is_missing"] & frame["kp"].notna()]
    if valid.empty:
        return None, None
    row = valid.iloc[-1]
    return pd.Timestamp(row["time_utc"]).to_pydatetime(), float(row["kp"])
