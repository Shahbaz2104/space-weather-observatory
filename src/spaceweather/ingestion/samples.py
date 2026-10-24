"""Loader for the versioned, genuine-data offline sample."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from spaceweather.attribution import GFZ_KP, NASA_OMNI
from spaceweather.config import Settings
from spaceweather.data_sources.base import KP_COLUMNS, SOLAR_WIND_COLUMNS, make_source_info
from spaceweather.logging_config import get_logger
from spaceweather.models import DataBundle, DataStatus

logger = get_logger("samples")

METADATA_FILE = "samples.json"


def _metadata(settings: Settings) -> dict[str, object]:
    path = settings.sample_dir / METADATA_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read sample metadata: %s", exc)
        return {}


def _block(metadata: dict[str, object], section: str) -> dict[str, object]:
    block = metadata.get(section)
    return block if isinstance(block, dict) else {}


def _retrieved_at(metadata: dict[str, object], section: str) -> datetime | None:
    value = _block(metadata, section).get("retrieved_at")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _as_utc(value: datetime | pd.Timestamp) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    return (
        timestamp.tz_localize("UTC")
        if timestamp.tzinfo is None
        else timestamp.tz_convert("UTC")
    )


def _filter(
    frame: pd.DataFrame, start: datetime | None, end: datetime | None
) -> pd.DataFrame:
    if frame.empty:
        return frame
    times = pd.to_datetime(frame["time_utc"], utc=True, errors="coerce")
    frame = frame.assign(time_utc=times).loc[lambda df: df["time_utc"].notna()]
    if start is not None:
        frame = frame.loc[frame["time_utc"] >= _as_utc(start)]
    if end is not None:
        frame = frame.loc[frame["time_utc"] <= _as_utc(end)]
    return frame.sort_values("time_utc").reset_index(drop=True)


def _normalize_kp(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["kp"] = pd.to_numeric(frame["kp"], errors="coerce")
    if "a_running" not in frame:
        frame["a_running"] = pd.array([pd.NA] * len(frame), dtype="Int64")
    if "station_count" not in frame:
        frame["station_count"] = pd.array([pd.NA] * len(frame), dtype="Int64")
    if "source" not in frame:
        frame["source"] = "GFZ"
    if "status" not in frame:
        frame["status"] = DataStatus.DEFINITIVE.value
    if "is_missing" not in frame:
        frame["is_missing"] = frame["kp"].isna()
    frame["is_missing"] = frame["is_missing"].astype(bool) | frame["kp"].isna()
    return frame[KP_COLUMNS]


def load_sample_kp(
    settings: Settings,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
) -> DataBundle:
    """Load genuine GFZ Kp observations bundled for offline demonstration."""
    metadata = _metadata(settings)
    frames = [
        _read_csv(settings.sample_dir / name)
        for name in ("kp_2003.csv", "kp_2024.csv")
    ]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return DataBundle(
            frame=pd.DataFrame(columns=KP_COLUMNS),
            mode="offline",
            is_sample=True,
            message="Offline sample is missing from data/samples.",
        )
    frame = _normalize_kp(pd.concat(frames, ignore_index=True))
    frame = _filter(frame, start, end)
    kp_metadata = _block(metadata, "kp")
    kp_url = kp_metadata.get("url")
    source = make_source_info(
        GFZ_KP,
        retrieved_at=_retrieved_at(metadata, "kp"),
        stale=True,
        from_cache=True,
        status=DataStatus.DEFINITIVE,
        url=kp_url if isinstance(kp_url, str) else GFZ_KP.url,
    )
    return DataBundle(
        frame=frame,
        sources=[source],
        mode="offline",
        is_sample=True,
        message="Offline demo: bundled GFZ Kp observations, not live data.",
        last_updated=source.retrieved_at,
        warnings=[
            "This is a versioned sample of genuine observations, not a live feed."
        ],
    )


def load_sample_solar_wind(
    settings: Settings,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
) -> DataBundle:
    """Load historical OMNI2 hourly measurements bundled for offline analysis."""
    metadata = _metadata(settings)
    frame = _read_csv(settings.sample_dir / "omni_2024_05.csv")
    if frame.empty:
        return DataBundle(
            frame=pd.DataFrame(columns=SOLAR_WIND_COLUMNS),
            mode="offline",
            is_sample=True,
            message="Offline solar-wind sample is missing from data/samples.",
        )
    frame = _filter(frame, start, end)
    for column in SOLAR_WIND_COLUMNS:
        if column not in frame:
            frame[column] = pd.NA
    frame["is_missing"] = frame["is_missing"].astype(bool)
    solar_wind_metadata = _block(metadata, "solar_wind")
    solar_wind_url = solar_wind_metadata.get("url")
    source = make_source_info(
        NASA_OMNI,
        retrieved_at=_retrieved_at(metadata, "solar_wind"),
        stale=True,
        from_cache=True,
        status=DataStatus.OBSERVED,
        url=solar_wind_url if isinstance(solar_wind_url, str) else NASA_OMNI.url,
    )
    return DataBundle(
        frame=frame[SOLAR_WIND_COLUMNS].reset_index(drop=True),
        sources=[source],
        mode="offline",
        is_sample=True,
        message="Offline demo: bundled OMNI2 hourly observations, not live data.",
        last_updated=source.retrieved_at,
        warnings=[
            "This is a versioned sample of genuine observations, not a live feed."
        ],
    )


def sample_kp_years(settings: Settings) -> list[int]:
    """Return the years represented in the bundled Kp sample."""
    years: set[int] = set()
    for name in ("kp_2003.csv", "kp_2024.csv"):
        frame = _read_csv(settings.sample_dir / name)
        if frame.empty:
            continue
        times = pd.to_datetime(frame["time_utc"], utc=True, errors="coerce")
        years.update(int(year) for year in times.dt.year.dropna().unique())
    return sorted(years)
