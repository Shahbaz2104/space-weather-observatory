"""Historical adapters for GFZ Kp and NASA OMNI2 data."""

from __future__ import annotations

import io

import pandas as pd

from spaceweather.attribution import GFZ_KP, NASA_OMNI
from spaceweather.config import Settings
from spaceweather.data_sources.base import (
    KP_COLUMNS,
    SOLAR_WIND_COLUMNS,
    attach_attrs,
    make_source_info,
)
from spaceweather.exceptions import SchemaValidationError
from spaceweather.ingestion.fetch import HttpClient
from spaceweather.ingestion.validate import (
    coerce_numeric,
    mask_fill_values,
    require_columns,
)
from spaceweather.logging_config import get_logger
from spaceweather.models import DataStatus, SourceInfo, ValidationIssue

logger = get_logger("historical")

GFZ_COLUMNS = [
    "year",
    "month",
    "day",
    "hour_start",
    "hour_mid",
    "days",
    "days_mid",
    "kp",
    "ap",
    "d",
]

GFZ_UNITS = {"kp": "unitless (0-9)", "ap": "nT (derived amplitude)"}

OMNI_COLUMNS = [
    "year", "doy", "hour", "rotation", "imf_spacecraft", "plasma_spacecraft",
    "n_imf", "n_plasma", "bt", "bmag", "b_lat", "b_long", "bx_gse", "by_gse",
    "bz_gse", "by_gsm", "bz_gsm", "sigma_bt", "sigma_b", "sigma_bx", "sigma_by",
    "sigma_bz", "temperature", "density", "speed", "flow_long", "flow_lat",
    "alpha_ratio", "pressure", "sigma_t", "sigma_n", "sigma_v", "sigma_phi",
    "sigma_theta", "sigma_alpha", "e_field", "beta", "alfven_mach", "kp_x10",
    "sunspot", "dst", "ae", "p1", "p2", "p4", "p10", "p30", "p60", "flag",
    "ap", "f107", "pcn", "al", "au", "magnetosonic_mach",
]

OMNI_UNITS = {
    "speed_kms": "km/s",
    "density_cm3": "protons/cm^3",
    "temperature_k": "K",
    "bz_gsm_nt": "nT (GSM)",
    "bt_nt": "nT",
}


def _validate_whitespace_width(
    text: str, *, expected: int, source: str
) -> None:
    """Reject truncated flat files instead of silently padding missing fields."""
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if len(fields) != expected:
            raise SchemaValidationError(
                f"{source}: line {line_number} has {len(fields)} fields; "
                f"expected {expected}"
            )


def _parse_utc_date_parts(
    years: pd.Series, months: pd.Series, days: pd.Series, hours: pd.Series
) -> pd.Series:
    base = pd.to_datetime(
        {
            "year": pd.to_numeric(years, errors="coerce"),
            "month": pd.to_numeric(months, errors="coerce"),
            "day": pd.to_numeric(days, errors="coerce"),
        },
        utc=True,
        errors="coerce",
    )
    return pd.Series(base, index=years.index) + pd.to_timedelta(
        pd.to_numeric(hours, errors="coerce"), unit="h"
    )


def parse_gfz_kp(text: str) -> tuple[pd.DataFrame, list[ValidationIssue]]:
    """Parse the GFZ Kp/ap fixed-format text file (one row per three hours)."""
    if not text.strip():
        raise SchemaValidationError("GFZ Kp response was empty")
    _validate_whitespace_width(text, expected=len(GFZ_COLUMNS), source="GFZ Kp")
    try:
        raw = pd.read_csv(
            io.StringIO(text),
            sep=r"\s+",
            comment="#",
            header=None,
            names=GFZ_COLUMNS,
            usecols=range(len(GFZ_COLUMNS)),
            engine="c",
        )
    except pd.errors.ParserError as exc:
        raise SchemaValidationError(f"Could not parse GFZ Kp file: {exc}") from exc
    if raw.empty:
        raise SchemaValidationError("GFZ Kp file contained no data rows")
    require_columns(raw, ["year", "month", "day", "hour_start", "kp", "ap", "d"], source="GFZ")

    issues: list[ValidationIssue] = []
    times = _parse_utc_date_parts(raw["year"], raw["month"], raw["day"], raw["hour_start"])
    invalid_times = int(times.isna().sum())
    if invalid_times:
        issues.append(
            ValidationIssue(
                level="warning",
                message="GFZ rows with an invalid timestamp were dropped.",
                count=invalid_times,
            )
        )

    kp = coerce_numeric(raw["kp"])
    missing_kp = kp < 0.0
    kp = kp.mask(missing_kp)
    invalid_range = kp.notna() & (kp > 9.0)
    if int(invalid_range.sum()):
        issues.append(
            ValidationIssue(
                level="warning",
                message="GFZ Kp values above 9 were treated as missing.",
                count=int(invalid_range.sum()),
            )
        )
        kp = kp.mask(invalid_range)

    ap_values = pd.to_numeric(raw["ap"], errors="coerce")
    ap = pd.array(ap_values.mask(ap_values < 0), dtype="Int64")

    d_flag = pd.to_numeric(raw["d"], errors="coerce").fillna(0).astype(int)
    status = d_flag.map(
        lambda value: DataStatus.DEFINITIVE.value
        if value >= 1
        else DataStatus.PRELIMINARY.value
    )

    frame = pd.DataFrame(
        {
            "time_utc": times,
            "kp": kp,
            "a_running": pd.array([pd.NA] * len(raw), dtype="Int64"),
            "station_count": pd.array([pd.NA] * len(raw), dtype="Int64"),
            "source": "GFZ",
            "status": status,
            "is_missing": kp.isna(),
            "ap": ap,
        }
    ).loc[lambda df: df["time_utc"].notna()]
    frame = frame.sort_values("time_utc").drop_duplicates("time_utc", keep="last")
    missing_count = int(frame["is_missing"].sum())
    if missing_count:
        issues.append(
            ValidationIssue(
                level="info",
                message="GFZ rows with Kp = -1 (missing) were retained and flagged.",
                count=missing_count,
            )
        )
    return frame.reset_index(drop=True), issues


def fetch_gfz_kp(client: HttpClient, settings: Settings) -> tuple[pd.DataFrame, SourceInfo]:
    """Retrieve the complete GFZ Kp record since 1932."""
    result = client.fetch(settings.gfz_kp_url, ttl_seconds=settings.historical_ttl_seconds)
    frame, issues = parse_gfz_kp(result.text())
    source = make_source_info(
        GFZ_KP,
        retrieved_at=result.retrieved_at,
        stale=result.stale,
        from_cache=result.from_cache,
        status=DataStatus.DEFINITIVE,
        url=result.url,
    )
    frame = attach_attrs(
        frame,
        source_info=source,
        units=GFZ_UNITS,
        issues=[issue.message for issue in issues],
    )
    logger.info(
        "Loaded %d GFZ Kp observations (%s to %s)",
        len(frame),
        frame["time_utc"].min(),
        frame["time_utc"].max(),
    )
    return frame[KP_COLUMNS], source


def parse_omni2(text: str, *, year: int) -> tuple[pd.DataFrame, list[ValidationIssue]]:
    """Parse one yearly OMNI2 hourly flat file."""
    if not text.strip():
        raise SchemaValidationError(f"OMNI2 {year} response was empty")
    _validate_whitespace_width(
        text, expected=len(OMNI_COLUMNS), source=f"OMNI2 {year}"
    )
    try:
        raw = pd.read_csv(
            io.StringIO(text),
            sep=r"\s+",
            header=None,
            names=OMNI_COLUMNS,
            engine="c",
        )
    except pd.errors.ParserError as exc:
        raise SchemaValidationError(f"Could not parse OMNI2 {year}: {exc}") from exc
    if raw.empty:
        raise SchemaValidationError(f"OMNI2 {year} contained no data rows")
    require_columns(
        raw,
        ["year", "doy", "hour", "bt", "bz_gsm", "temperature", "density", "speed"],
        source=f"OMNI2 {year}",
    )

    issues: list[ValidationIssue] = []
    start = pd.Timestamp(f"{year}-01-01T00:00:00Z")
    times = (
        start
        + pd.to_timedelta(pd.to_numeric(raw["doy"], errors="coerce") - 1, unit="D")
        + pd.to_timedelta(pd.to_numeric(raw["hour"], errors="coerce"), unit="h")
    )
    valid_time = times.notna()
    bt = mask_fill_values(raw["bt"], threshold=999.0)
    bz = mask_fill_values(raw["bz_gsm"], threshold=999.0)
    temperature = mask_fill_values(raw["temperature"], threshold=9_999_999.0)
    density = mask_fill_values(raw["density"], threshold=999.0)
    speed = mask_fill_values(raw["speed"], threshold=9999.0)

    frame = pd.DataFrame(
        {
            "time_utc": pd.Series(times, index=raw.index),
            "speed_kms": speed,
            "density_cm3": density,
            "temperature_k": temperature,
            "bz_gsm_nt": bz,
            "bt_nt": bt,
            "source": "NASA OMNI2",
            "status": DataStatus.OBSERVED.value,
        }
    ).loc[valid_time]
    frame["is_missing"] = frame[
        ["speed_kms", "density_cm3", "bz_gsm_nt", "bt_nt"]
    ].isna().all(axis=1)
    frame = frame.sort_values("time_utc").drop_duplicates("time_utc", keep="last")
    missing_count = int(frame["is_missing"].sum())
    if missing_count:
        issues.append(
            ValidationIssue(
                level="info",
                message="OMNI2 hours with all selected fields missing were retained and flagged.",
                count=missing_count,
            )
        )
    return frame.reset_index(drop=True)[SOLAR_WIND_COLUMNS], issues


def fetch_omni_year(
    client: HttpClient, settings: Settings, year: int
) -> tuple[pd.DataFrame, SourceInfo]:
    """Retrieve one year of hourly OMNI2 solar-wind measurements."""
    if year < 1963:
        raise ValueError("OMNI2 data begin in 1963")
    url = settings.omni_url_template.format(year=year)
    result = client.fetch(url, ttl_seconds=settings.historical_ttl_seconds)
    frame, issues = parse_omni2(result.text(), year=year)
    source = make_source_info(
        NASA_OMNI,
        retrieved_at=result.retrieved_at,
        stale=result.stale,
        from_cache=result.from_cache,
        status=DataStatus.OBSERVED,
        url=result.url,
    )
    frame = attach_attrs(
        frame,
        source_info=source,
        units=OMNI_UNITS,
        issues=[issue.message for issue in issues],
    )
    logger.info("Loaded %d OMNI2 hourly rows for %d", len(frame), year)
    return frame, source
