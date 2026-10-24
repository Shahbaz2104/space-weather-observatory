"""GFZ Kp and OMNI2 flat-file parsing tests."""

from __future__ import annotations

import pandas as pd
import pytest

from spaceweather.data_sources.historical import parse_gfz_kp, parse_omni2
from spaceweather.exceptions import SchemaValidationError

GFZ_TEXT = """\
# PURPOSE: test fixture
# Kp, ap and Ap
2024 05 01 00.0 01.50 0.00000 0.06250 5.0 48 1
2024 05 01 03.0 04.50 0.12500 0.18750 6.0 80 1
2024 05 01 06.0 07.50 0.25000 0.31250 -1 0 0
2024 05 01 09.0 10.50 0.37500 0.43750 9.5 400 1
"""


def test_gfz_parses_interval_start_and_flags() -> None:
    frame, issues = parse_gfz_kp(GFZ_TEXT)
    assert len(frame) == 4
    assert frame.iloc[0]["time_utc"] == pd.Timestamp("2024-05-01T00:00:00Z")
    assert frame.iloc[1]["time_utc"] == pd.Timestamp("2024-05-01T03:00:00Z")
    assert frame.iloc[0]["kp"] == 5.0
    assert frame.iloc[0]["ap"] == 48
    assert frame.iloc[2]["is_missing"]
    assert pd.isna(frame.iloc[3]["kp"])
    assert frame.iloc[0]["status"] == "definitive"
    assert frame.iloc[2]["status"] == "preliminary"
    assert any(issue.level == "warning" for issue in issues)
    assert all(frame["source"] == "GFZ")


def test_gfz_rejects_empty_payload() -> None:
    with pytest.raises(SchemaValidationError, match="empty"):
        parse_gfz_kp("   \n")


def _omni_row(
    *,
    doy: str = "122",
    hour: str = "0",
    speed: str = "450.0",
    density: str = "5.2",
    temperature: str = "120000",
    bt: str = "8.0",
    bz: str = "-4.0",
) -> str:
    fields = ["0"] * 55
    fields[0] = "2024"
    fields[1] = doy
    fields[2] = hour
    fields[8] = bt
    fields[16] = bz
    fields[22] = temperature
    fields[23] = density
    fields[24] = speed
    return " ".join(fields)


def test_omni_parses_hourly_record_and_masks_fill() -> None:
    text = "\n".join(
        [
            _omni_row(),
            _omni_row(
                hour="1",
                speed="9999.9",
                density="999.9",
                temperature="9999999.9",
                bt="999.9",
                bz="999.9",
            ),
            _omni_row(doy="bad", hour="2"),
        ]
    )
    frame, issues = parse_omni2(text, year=2024)
    assert len(frame) == 2
    assert frame.iloc[0]["time_utc"] == pd.Timestamp("2024-05-01T00:00:00Z")
    assert frame.iloc[0]["speed_kms"] == 450.0
    assert frame.iloc[0]["bz_gsm_nt"] == -4.0
    assert frame.iloc[1][["speed_kms", "density_cm3", "bz_gsm_nt", "bt_nt"]].isna().all()
    assert bool(frame.iloc[1]["is_missing"])
    assert all(frame["source"] == "NASA OMNI2")
    assert all(frame["status"] == "observed")
    assert issues


def test_omni_rejects_bad_width() -> None:
    with pytest.raises(SchemaValidationError, match="fields"):
        parse_omni2("2024 122 0\n2024 122 1", year=2024)
