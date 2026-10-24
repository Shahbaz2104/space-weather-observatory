"""Provenance and download helpers for exported data and figures."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pandas as pd

from spaceweather.models import AnimationConfig, DataBundle, Provenance

DEFAULT_UNITS = {
    "time_utc": "UTC timestamp",
    "kp": "unitless (0-9)",
    "a_running": "nT (derived amplitude)",
    "station_count": "stations",
    "speed_kms": "km/s",
    "density_cm3": "protons/cm^3",
    "temperature_k": "K",
    "bz_gsm_nt": "nT (GSM)",
    "bt_nt": "nT",
}


def software_version() -> str:
    """Return the installed distribution version or the source version."""
    try:
        return version("space-weather-observatory")
    except PackageNotFoundError:
        from spaceweather import __version__

        return __version__


def build_provenance(
    bundle: DataBundle,
    *,
    threshold: float,
    transformations: list[str] | None = None,
    animation: AnimationConfig | None = None,
    extra_notes: dict[str, object] | None = None,
) -> Provenance:
    """Describe exactly how an exported artifact was produced."""
    frame = bundle.frame
    window: tuple[datetime, datetime] | None = None
    if not frame.empty and "time_utc" in frame:
        times = pd.to_datetime(frame["time_utc"], utc=True, errors="coerce").dropna()
        if not times.empty:
            window = (
                times.min().to_pydatetime(),
                times.max().to_pydatetime(),
            )
    units = {**DEFAULT_UNITS, **dict(frame.attrs.get("units", {}))}
    notes: dict[str, object] = {
        "data_mode": bundle.mode,
        "is_sample": bundle.is_sample,
        "warnings": list(bundle.warnings),
        "threshold_kp": threshold,
        "source_details": [
            source.model_dump(mode="json") for source in bundle.sources
        ],
    }
    if extra_notes:
        notes.update(extra_notes)
    return Provenance(
        software_version=software_version(),
        created_at=datetime.now(UTC),
        source_urls=sorted({source.url for source in bundle.sources}),
        retrieved_at=[source.retrieved_at for source in bundle.sources if source.retrieved_at],
        time_window_utc=window,
        units=units,
        transformations=[
            "Filtered to the selected UTC window.",
            "No interpolation or zero-filling of missing observations.",
            *(transformations or []),
        ],
        animation=animation,
        notes=notes,
    )


def provenance_json_bytes(provenance: Provenance) -> bytes:
    """Serialize provenance as stable, human-readable JSON."""
    payload = provenance.model_dump(mode="json")
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def write_provenance(provenance: Provenance, path: str | Path) -> Path:
    """Write a provenance JSON file and return its path."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(provenance_json_bytes(provenance))
    return output


def frame_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    """Serialize a dataframe as UTF-8 CSV with ISO-8601 UTC timestamps."""
    output = frame.copy()
    for column in output.columns:
        if pd.api.types.is_datetime64_any_dtype(output[column]):
            output[column] = pd.to_datetime(output[column], utc=True).dt.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
    return output.to_csv(index=False).encode("utf-8")


def frame_to_parquet_bytes(frame: pd.DataFrame) -> bytes:
    """Serialize a dataframe as Parquet in memory."""
    return frame.to_parquet(index=False)


def write_export_bundle(
    frame: pd.DataFrame,
    provenance: Provenance,
    *,
    directory: str | Path,
    stem: str,
) -> dict[str, Path]:
    """Write CSV, Parquet, and provenance metadata for one result."""
    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{stem}.csv"
    parquet_path = output_dir / f"{stem}.parquet"
    provenance_path = output_dir / f"{stem}.provenance.json"
    csv_path.write_bytes(frame_to_csv_bytes(frame))
    parquet_path.write_bytes(frame_to_parquet_bytes(frame))
    write_provenance(provenance, provenance_path)
    return {
        "csv": csv_path,
        "parquet": parquet_path,
        "provenance": provenance_path,
    }
