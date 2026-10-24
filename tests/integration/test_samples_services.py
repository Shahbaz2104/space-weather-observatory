"""Offline samples and service-level integration through real loader paths."""

from __future__ import annotations

import pandas as pd

from spaceweather.config import get_settings
from spaceweather.ingestion.samples import load_sample_kp, load_sample_solar_wind
from spaceweather.services import (
    load_correlation_data,
    load_kp_window,
    load_solar_wind_window,
)


def test_sample_kp_is_genuine_and_complete() -> None:
    settings = get_settings()
    result = load_sample_kp(settings)
    assert len(result.frame) > 5_000
    assert result.is_sample
    assert result.sources
    assert result.sources[0].key == "gfz_kp"
    assert result.frame["kp"].between(0.0, 9.0).all()
    assert result.frame["kp"].max() == 9.0
    assert result.frame["time_utc"].is_monotonic_increasing
    assert not result.frame["is_missing"].any()


def test_sample_solar_wind_is_hourly_and_has_no_zero_fill() -> None:
    settings = get_settings()
    result = load_sample_solar_wind(settings)
    assert len(result.frame) == 744
    assert result.is_sample
    assert result.sources[0].key == "nasa_omni"
    assert int(result.frame["speed_kms"].isna().sum()) == 21
    assert (result.frame["speed_kms"].dropna() > 0.0).all()
    assert (result.frame["density_cm3"].dropna() > 0.0).all()
    assert result.frame["bz_gsm_nt"].min() < -10.0
    deltas = result.frame["time_utc"].diff().dropna().unique()
    assert len(deltas) == 1
    assert pd.Timedelta(deltas[0]) == pd.Timedelta(hours=1)


def test_offline_kp_and_wind_windows_use_samples() -> None:
    window = {
        "start": pd.Timestamp("2024-05-01"),
        "end": pd.Timestamp("2024-05-11"),
    }
    kp = load_kp_window("offline", **window)
    wind = load_solar_wind_window("offline", **window)
    assert kp.is_sample and wind.is_sample
    assert not kp.frame.empty and not wind.frame.empty
    assert kp.frame["time_utc"].min() >= pd.Timestamp("2024-05-01T00:00:00Z")


def test_offline_correlation_pairs_may_2024() -> None:
    kp_bundle, wind_bundle, aligned = load_correlation_data(
        "offline",
        start=pd.Timestamp("2024-05-01"),
        end=pd.Timestamp("2024-06-01"),
    )
    assert kp_bundle.is_sample and wind_bundle.is_sample
    assert not aligned.empty
    assert len(aligned) == 248
    assert aligned["kp"].between(0.0, 9.0).all()
    assert 240 <= aligned["speed_kms"].notna().sum() < 248
    assert aligned["coverage_fraction"].between(0.0, 1.0).all()
