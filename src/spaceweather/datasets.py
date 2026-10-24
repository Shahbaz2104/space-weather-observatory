"""Build the versioned, genuine-data sample used for offline operation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from spaceweather.attribution import GFZ_KP, NASA_OMNI, NOAA_SWPC
from spaceweather.config import Settings
from spaceweather.data_sources.historical import fetch_gfz_kp, fetch_omni_year
from spaceweather.data_sources.noaa import fetch_recent_kp
from spaceweather.ingestion.cache import FileCache
from spaceweather.ingestion.fetch import HttpClient
from spaceweather.logging_config import get_logger

logger = get_logger("datasets")

KP_SAMPLE_COLUMNS = [
    "time_utc",
    "kp",
    "a_running",
    "station_count",
    "source",
    "status",
    "is_missing",
]
SOLAR_WIND_SAMPLE_COLUMNS = [
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


@dataclass(frozen=True)
class SampleBuildResult:
    """Summary of a completed sample build."""

    rows_2003: int
    rows_2024: int
    rows_solar_wind: int
    metadata_path: Path
    processed_path: Path | None


def _iso(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_kp_year(frame: pd.DataFrame, year: int, path: Path) -> int:
    subset = frame.loc[pd.to_datetime(frame["time_utc"], utc=True).dt.year == year]
    output = subset[KP_SAMPLE_COLUMNS].copy()
    output["time_utc"] = _iso(output["time_utc"])
    output.to_csv(path, index=False)
    logger.info("Wrote %d Kp rows for %d to %s", len(output), year, path.name)
    return len(output)


def _write_omni_month(frame: pd.DataFrame, path: Path, month: str) -> int:
    times = pd.to_datetime(frame["time_utc"], utc=True)
    subset = frame.loc[times.dt.strftime("%Y-%m") == month]
    output = subset[SOLAR_WIND_SAMPLE_COLUMNS].copy()
    output["time_utc"] = _iso(output["time_utc"])
    output.to_csv(path, index=False)
    logger.info("Wrote %d OMNI rows for %s to %s", len(output), month, path.name)
    return len(output)


def build_samples(
    settings: Settings, *, write_processed: bool = True
) -> SampleBuildResult:
    """Download sources and write the small, genuine offline sample."""
    settings.ensure_directories()
    with HttpClient(settings, cache=FileCache(settings.cache_dir)) as client:
        gfz_frame, gfz_source = fetch_gfz_kp(client, settings)
        noaa_frame, noaa_source = fetch_recent_kp(client, settings)
        omni_frame, omni_source = fetch_omni_year(client, settings, 2024)

    rows_2003 = _write_kp_year(gfz_frame, 2003, settings.sample_dir / "kp_2003.csv")
    rows_2024 = _write_kp_year(gfz_frame, 2024, settings.sample_dir / "kp_2024.csv")
    rows_wind = _write_omni_month(
        omni_frame, settings.sample_dir / "omni_2024_05.csv", "2024-05"
    )

    processed_path: Path | None = None
    if write_processed:
        combined = pd.concat([gfz_frame, noaa_frame], ignore_index=True)
        combined = combined.sort_values("time_utc").drop_duplicates(
            "time_utc", keep="last"
        )
        processed_path = settings.processed_dir / "kp_combined.parquet"
        combined.to_parquet(processed_path, index=False)
        logger.info("Wrote %d combined Kp rows to %s", len(combined), processed_path)

    metadata = {
        "created_at": datetime.now(UTC).isoformat(),
        "description": (
            "Versioned sample of genuine observations for offline demonstration. "
            "These are not live data."
        ),
        "kp": {
            "files": ["kp_2003.csv", "kp_2024.csv"],
            "source": GFZ_KP.name,
            "url": settings.gfz_kp_url,
            "license": GFZ_KP.license,
            "citation": GFZ_KP.citation,
            "retrieved_at": (
                gfz_source.retrieved_at.isoformat()
                if gfz_source.retrieved_at
                else None
            ),
            "rows": {"2003": rows_2003, "2024": rows_2024},
            "columns": {
                "time_utc": "UTC timestamp at the start of a three-hour Kp interval",
                "kp": "planetary Kp index, unitless 0-9",
                "status": "definitive or preliminary",
                "source": "GFZ",
            },
        },
        "solar_wind": {
            "file": "omni_2024_05.csv",
            "source": NASA_OMNI.name,
            "url": settings.omni_url_template.format(year=2024),
            "license": NASA_OMNI.license,
            "citation": NASA_OMNI.citation,
            "retrieved_at": (
                omni_source.retrieved_at.isoformat()
                if omni_source.retrieved_at
                else None
            ),
            "rows": rows_wind,
            "columns": {
                "time_utc": "UTC hourly timestamp",
                "speed_kms": "proton flow speed, km/s",
                "density_cm3": "proton density, particles/cm^3",
                "temperature_k": "proton temperature, K",
                "bz_gsm_nt": "IMF Bz in GSM coordinates, nT",
                "bt_nt": "IMF field magnitude, nT",
            },
        },
        "recent_reference": {
            "source": NOAA_SWPC.name,
            "url": settings.recent_kp_url,
            "retrieved_at": (
                noaa_source.retrieved_at.isoformat()
                if noaa_source.retrieved_at
                else None
            ),
        },
    }
    metadata_path = settings.sample_dir / "samples.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Wrote sample metadata to %s", metadata_path)
    return SampleBuildResult(
        rows_2003=rows_2003,
        rows_2024=rows_2024,
        rows_solar_wind=rows_wind,
        metadata_path=metadata_path,
        processed_path=processed_path,
    )
