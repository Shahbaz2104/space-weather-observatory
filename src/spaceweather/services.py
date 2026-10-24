"""High-level data access used by the dashboard, scripts, and tests."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache

import pandas as pd

from spaceweather.config import Settings, get_settings
from spaceweather.data_sources.historical import fetch_gfz_kp, fetch_omni_year
from spaceweather.data_sources.noaa import fetch_propagated_solar_wind, fetch_recent_kp
from spaceweather.exceptions import SourceError
from spaceweather.ingestion.cache import FileCache
from spaceweather.ingestion.fetch import HttpClient
from spaceweather.ingestion.samples import load_sample_kp, load_sample_solar_wind
from spaceweather.logging_config import get_logger
from spaceweather.models import DataBundle, SourceInfo
from spaceweather.processing.cleaning import filter_time_range, merge_kp_sources
from spaceweather.processing.resampling import align_solar_wind_with_kp

logger = get_logger("services")

MAX_SOLAR_WIND_YEARS = 3


def _client(settings: Settings) -> HttpClient:
    return HttpClient(settings, cache=FileCache(settings.cache_dir))


def _now() -> pd.Timestamp:
    return pd.Timestamp.now(tz="UTC")


def resolve_window(
    *,
    days: int | None = None,
    start: datetime | pd.Timestamp | None = None,
    end: datetime | pd.Timestamp | None = None,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Resolve a start/end window in UTC, defaulting to the last ``days`` days."""
    end_ts = pd.Timestamp(end) if end is not None else _now()
    if end_ts.tzinfo is None:
        end_ts = end_ts.tz_localize("UTC")
    if start is not None:
        start_ts = pd.Timestamp(start)
        if start_ts.tzinfo is None:
            start_ts = start_ts.tz_localize("UTC")
    elif days is not None:
        start_ts = end_ts - pd.Timedelta(days=days)
    else:
        start_ts = end_ts - pd.Timedelta(days=7)
    if start_ts > end_ts:
        raise ValueError("start must not be after end")
    return start_ts, end_ts


@lru_cache(maxsize=2)
def _cached_gfz(cache_dir: str, historical_ttl: int, recent_ttl: int, retries: int) -> DataBundle:
    settings = get_settings()
    with _client(settings) as client:
        frame, source = fetch_gfz_kp(client, settings)
    return DataBundle(
        frame=frame,
        sources=[source],
        mode="live",
        last_updated=source.retrieved_at,
        message="GFZ definitive and preliminary Kp observations.",
    )


@lru_cache(maxsize=2)
def _cached_noaa(cache_dir: str, ttl: int) -> DataBundle:
    settings = get_settings()
    with _client(settings) as client:
        frame, source = fetch_recent_kp(client, settings)
    return DataBundle(
        frame=frame,
        sources=[source],
        mode="live",
        last_updated=source.retrieved_at,
        message="NOAA SWPC recent observed Kp (preliminary).",
    )


def _settings_key(settings: Settings) -> tuple[str, int, int, int]:
    return (
        str(settings.cache_dir),
        settings.historical_ttl_seconds,
        settings.recent_kp_ttl_seconds,
        settings.http_retries,
    )


def load_gfz_bundle(settings: Settings | None = None) -> DataBundle:
    """Load the full GFZ Kp record (cached per process)."""
    settings = settings or get_settings()
    key = _settings_key(settings)
    bundle = _cached_gfz(*key)
    return DataBundle(
        frame=bundle.frame.copy(),
        sources=list(bundle.sources),
        mode="live",
        last_updated=bundle.last_updated,
        message=bundle.message,
    )


def load_noaa_bundle(settings: Settings | None = None) -> DataBundle:
    """Load the recent NOAA Kp record (cached per process)."""
    settings = settings or get_settings()
    key = _settings_key(settings)
    bundle = _cached_noaa(key[0], key[2])
    return DataBundle(
        frame=bundle.frame.copy(),
        sources=list(bundle.sources),
        mode="live",
        last_updated=bundle.last_updated,
        message=bundle.message,
    )


def _annotate(
    bundle: DataBundle,
    *,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
) -> DataBundle:
    if start is not None and end is not None and not bundle.frame.empty:
        frame = filter_time_range(bundle.frame, start, end)
        frame.attrs.update(bundle.frame.attrs)
        bundle.frame = frame
    return bundle


def _sample_fallback(
    settings: Settings,
    *,
    mode: str,
    reason: str,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    solar_wind: bool = False,
) -> DataBundle:
    bundle = (
        load_sample_solar_wind(settings, start=start, end=end)
        if solar_wind
        else load_sample_kp(settings, start=start, end=end)
    )
    if bundle.frame.empty:
        full = (
            load_sample_solar_wind(settings)
            if solar_wind
            else load_sample_kp(settings)
        )
        if not full.frame.empty:
            bundle = full
    bundle.mode = mode
    bundle.warnings.append(reason)
    logger.warning("Falling back to bundled sample: %s", reason)
    return bundle


def available_kp_window(mode: str = "auto", settings: Settings | None = None) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Return the available Kp range for the selected mode."""
    settings = settings or get_settings()
    if mode == "offline" or settings.offline_mode:
        bundle = load_sample_kp(settings)
    else:
        try:
            bundle = load_noaa_bundle(settings)
        except SourceError:
            bundle = load_sample_kp(settings)
    if bundle.frame.empty:
        now = _now()
        return now - pd.Timedelta(days=7), now
    times = pd.to_datetime(bundle.frame["time_utc"], utc=True)
    return times.min(), times.max()


def load_kp_window(
    mode: str = "auto",
    *,
    start: datetime | pd.Timestamp | None = None,
    end: datetime | pd.Timestamp | None = None,
    days: int | None = None,
    settings: Settings | None = None,
) -> DataBundle:
    """Load Kp for a window, choosing the authoritative source transparently."""
    settings = settings or get_settings()
    if mode not in {"auto", "live", "offline"}:
        raise ValueError(f"Unknown data mode: {mode}")
    if mode == "offline" or settings.offline_mode:
        if start is None and end is None and days is not None:
            start_ts, end_ts = resolve_window(days=days)
            return _annotate(load_sample_kp(settings), start=start_ts, end=end_ts)
        return load_sample_kp(settings, start=start, end=end)

    start_ts, end_ts = resolve_window(days=days, start=start, end=end)
    span_days = (end_ts - start_ts).total_seconds() / 86_400.0
    recent_end = end_ts >= _now() - pd.Timedelta(days=2)
    try:
        if span_days <= 7.0 and recent_end:
            bundle = load_noaa_bundle(settings)
            return _annotate(bundle, start=start_ts, end=end_ts)
        bundle = load_gfz_bundle(settings)
        if recent_end:
            try:
                recent = load_noaa_bundle(settings)
                merged = merge_kp_sources(recent.frame, bundle.frame)
                merged.attrs["source_info"] = recent.sources[0] if recent.sources else None
                bundle.frame = merged
                bundle.sources = list(bundle.sources) + list(recent.sources)
                bundle.last_updated = recent.last_updated
                bundle.message = (
                    "GFZ historical Kp with recent NOAA observations merged; "
                    "duplicate timestamps prefer the NOAA value."
                )
            except SourceError as exc:
                bundle.warnings.append(f"Recent NOAA observations unavailable: {exc}")
        return _annotate(bundle, start=start_ts, end=end_ts)
    except SourceError as exc:
        if mode == "live":
            raise
        return _sample_fallback(
            settings,
            mode=mode,
            reason=f"Live source unavailable ({exc}); showing bundled sample.",
            start=start_ts,
            end=end_ts,
        )


def load_kp_historical(
    mode: str = "auto", *, settings: Settings | None = None
) -> DataBundle:
    """Load the full available Kp record for heatmaps and long-range analyses."""
    settings = settings or get_settings()
    if mode == "offline" or settings.offline_mode:
        return load_sample_kp(settings)
    try:
        return load_gfz_bundle(settings)
    except SourceError as exc:
        if mode == "live":
            raise
        return _sample_fallback(
            settings,
            mode=mode,
            reason=f"Historical source unavailable ({exc}); showing bundled sample.",
        )


def available_solar_wind_window(
    mode: str = "auto", settings: Settings | None = None
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Return the available solar-wind range for the selected mode."""
    settings = settings or get_settings()
    if mode == "offline" or settings.offline_mode:
        bundle = load_sample_solar_wind(settings)
        if bundle.frame.empty:
            now = _now()
            return now - pd.Timedelta(days=7), now
        times = pd.to_datetime(bundle.frame["time_utc"], utc=True)
        return times.min(), times.max()
    now = _now()
    return now - pd.Timedelta(days=7), now


def load_solar_wind_window(
    mode: str = "auto",
    *,
    start: datetime | pd.Timestamp | None = None,
    end: datetime | pd.Timestamp | None = None,
    days: int | None = None,
    settings: Settings | None = None,
) -> DataBundle:
    """Load solar-wind measurements for a window."""
    settings = settings or get_settings()
    if mode not in {"auto", "live", "offline"}:
        raise ValueError(f"Unknown data mode: {mode}")
    start_ts, end_ts = resolve_window(days=days, start=start, end=end)
    if mode == "offline" or settings.offline_mode:
        bundle = load_sample_solar_wind(settings, start=start_ts, end=end_ts)
        return _annotate(bundle, start=start_ts, end=end_ts)

    span_days = (end_ts - start_ts).total_seconds() / 86_400.0
    try:
        if span_days <= 7.0 and end_ts >= _now() - pd.Timedelta(days=2):
            with _client(settings) as client:
                frame, source = fetch_propagated_solar_wind(client, settings)
            bundle = DataBundle(
                frame=frame,
                sources=[source],
                mode="live",
                last_updated=source.retrieved_at,
                message=(
                    "NOAA SWPC seven-day propagated (modeled) solar wind; "
                    "one-minute cadence, not a direct in-situ measurement at Earth."
                ),
            )
            return _annotate(bundle, start=start_ts, end=end_ts)

        years = sorted({start_ts.year, end_ts.year})
        if len(years) > MAX_SOLAR_WIND_YEARS:
            raise ValueError(
                f"Solar-wind history is limited to {MAX_SOLAR_WIND_YEARS} years per request."
            )
        frames: list[pd.DataFrame] = []
        sources: list[SourceInfo] = []
        with _client(settings) as client:
            for year in years:
                frame, source = fetch_omni_year(client, settings, year)
                frames.append(frame)
                sources.append(source)
        combined = pd.concat(frames, ignore_index=True)
        bundle = DataBundle(
            frame=combined,
            sources=sources,
            mode="live",
            last_updated=max(
                (source.retrieved_at for source in sources if source.retrieved_at),
                default=None,
            ),
            message="NASA OMNI2 hourly solar-wind observations.",
        )
        return _annotate(bundle, start=start_ts, end=end_ts)
    except SourceError as exc:
        if mode == "live":
            raise
        return _sample_fallback(
            settings,
            mode=mode,
            reason=f"Live solar-wind source unavailable ({exc}); showing bundled sample.",
            start=start_ts,
            end=end_ts,
            solar_wind=True,
        )


def load_correlation_data(
    mode: str = "auto",
    *,
    start: datetime | pd.Timestamp | None = None,
    end: datetime | pd.Timestamp | None = None,
    days: int | None = None,
    settings: Settings | None = None,
) -> tuple[DataBundle, DataBundle, pd.DataFrame]:
    """Load and align Kp with solar wind for correlation analysis."""
    settings = settings or get_settings()
    start_ts, end_ts = resolve_window(days=days, start=start, end=end)
    kp_bundle = load_kp_window(
        mode, start=start_ts, end=end_ts, settings=settings
    )
    wind_bundle = load_solar_wind_window(
        mode, start=start_ts, end=end_ts, settings=settings
    )
    aligned = align_solar_wind_with_kp(wind_bundle.frame, kp_bundle.frame)
    return kp_bundle, wind_bundle, aligned
