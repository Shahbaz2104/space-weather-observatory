"""NOAA payload parsing, fill masking, and modeled-wind labeling."""

from __future__ import annotations

import pandas as pd
import pytest

from spaceweather.data_sources.noaa import (
    parse_propagated_solar_wind,
    parse_recent_kp,
)
from spaceweather.exceptions import SchemaValidationError


def test_recent_kp_accepts_header_rows_and_skips_invalid() -> None:
    payload = [
        ["time_tag", "Kp", "a_running", "station_count"],
        ["2024-05-10T00:00:00", "5.0", "48", "8"],
        ["not-a-time", "7.0", "80", "8"],
        ["2024-05-10T03:00:00", "9.5", "400", "8"],
    ]
    frame, issues = parse_recent_kp(payload)
    assert len(frame) == 2
    assert frame["time_utc"].dt.tz is not None
    assert frame.iloc[0]["kp"] == 5.0
    assert frame.iloc[0]["a_running"] == 48
    assert pd.isna(frame.iloc[1]["kp"])
    assert bool(frame.iloc[1]["is_missing"])
    assert all(frame["status"] == "preliminary")
    assert any(issue.count == 1 for issue in issues)


def test_recent_kp_requires_time_and_kp() -> None:
    with pytest.raises(SchemaValidationError, match="required columns"):
        parse_recent_kp([{"time_tag": "2024-05-10T00:00:00"}])


def test_propagated_wind_masks_fill_values_and_marks_estimated() -> None:
    payload = [
        {
            "time_tag": "2024-05-10T00:00:00",
            "speed": 450.0,
            "density": 5.2,
            "bz": -4.0,
            "bt": 8.0,
            "temperature": 120_000.0,
        },
        {
            "time_tag": "2024-05-10T00:01:00",
            "speed": 9999.9,
            "density": 999.9,
            "bz": 999.9,
            "bt": 999.9,
            "temperature": 9_999_999.9,
        },
        {
            "time_tag": "2024-05-10T00:02:00",
            "speed": "bad",
            "density": None,
            "bz": None,
            "bt": None,
            "temperature": None,
        },
    ]
    frame, issues = parse_propagated_solar_wind(payload)
    assert len(frame) == 3
    assert frame.iloc[0]["speed_kms"] == 450.0
    assert frame.iloc[1][["speed_kms", "density_cm3", "bz_gsm_nt", "bt_nt"]].isna().all()
    assert bool(frame.iloc[1]["is_missing"])
    assert pd.isna(frame.iloc[2]["speed_kms"])
    assert all(frame["status"] == "estimated")
    assert any("all solar-wind fields" in issue.message for issue in issues)


def test_propagated_wind_requires_core_columns() -> None:
    with pytest.raises(SchemaValidationError, match="required columns"):
        parse_propagated_solar_wind(
            [{"time_tag": "2024-05-10T00:00:00", "speed": 400.0}]
        )
