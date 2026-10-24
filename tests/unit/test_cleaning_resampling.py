"""Window filtering, completeness, and solar-wind bin alignment."""

from __future__ import annotations

import pandas as pd
import pytest

from spaceweather.processing.cleaning import (
    data_completeness,
    expected_kp_samples,
    filter_time_range,
    missing_summary,
)
from spaceweather.processing.resampling import (
    aggregate_solar_wind,
    align_solar_wind_with_kp,
    infer_cadence_minutes,
)


def test_expected_slots_and_completeness(kp_frame_factory) -> None:
    assert expected_kp_samples("2024-05-10T00:00:00Z", "2024-05-10T06:00:00Z") == 3
    frame = kp_frame_factory(
        [
            ("2024-05-10T00:00:00", 4.0),
            ("2024-05-10T03:00:00", None),
            ("2024-05-10T06:00:00", 5.0),
        ]
    )
    assert data_completeness(
        frame, start="2024-05-10T00:00:00Z", end="2024-05-10T06:00:00Z"
    ) == pytest.approx(2 / 3)
    summary = missing_summary(
        frame, start="2024-05-10T00:00:00Z", end="2024-05-10T06:00:00Z"
    )
    assert summary["total_rows"] == 3
    assert summary["valid_rows"] == 2
    assert summary["missing_rows"] == 1
    assert summary["expected_slots"] == 3


def test_filter_time_range_is_end_exclusive(kp_frame_factory) -> None:
    frame = kp_frame_factory(
        [
            ("2024-05-10T00:00:00", 1.0),
            ("2024-05-10T03:00:00", 2.0),
            ("2024-05-10T06:00:00", 3.0),
        ]
    )
    filtered = filter_time_range(
        frame,
        pd.Timestamp("2024-05-10T00:00:00Z"),
        pd.Timestamp("2024-05-10T06:00:00Z"),
        inclusive=False,
    )
    assert list(filtered["kp"]) == [1.0, 2.0]


def _wind_frame() -> pd.DataFrame:
    times = pd.date_range("2024-05-10T00:00:00Z", periods=180, freq="1min")
    return pd.DataFrame(
        {
            "time_utc": times,
            "speed_kms": 400.0,
            "density_cm3": 5.0,
            "bz_gsm_nt": -2.0,
            "bt_nt": 8.0,
            "source": "test",
            "status": "observed",
            "is_missing": False,
        }
    )


def test_aggregate_solar_wind_uses_left_labels() -> None:
    aggregated = aggregate_solar_wind(_wind_frame())
    assert len(aggregated) == 1
    row = aggregated.iloc[0]
    assert row["time_utc"] == pd.Timestamp("2024-05-10T00:00:00Z")
    assert row["speed_kms"] == pytest.approx(400.0)
    assert int(row["n_samples"]) == 180
    assert row["coverage_fraction"] == pytest.approx(1.0)


def test_alignment_is_inner_join(kp_frame_factory) -> None:
    kp = kp_frame_factory(
        [
            ("2024-05-10T00:00:00", 4.0),
            ("2024-05-10T03:00:00", 5.0),
        ]
    )
    wind = _wind_frame()
    aligned = align_solar_wind_with_kp(wind, kp)
    assert len(aligned) == 1
    assert aligned.iloc[0]["kp"] == 4.0
    assert aligned.iloc[0]["speed_kms"] == pytest.approx(400.0)


def test_empty_wind_does_not_become_zero() -> None:
    empty = pd.DataFrame(columns=["time_utc", "speed_kms", "density_cm3", "bz_gsm_nt"])
    aggregated = aggregate_solar_wind(empty)
    assert aggregated.empty
    assert infer_cadence_minutes(empty) is None
