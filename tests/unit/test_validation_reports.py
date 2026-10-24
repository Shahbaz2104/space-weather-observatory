"""Shared validation helpers and provenance serialization."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from spaceweather.exceptions import SchemaValidationError
from spaceweather.export.reports import (
    build_provenance,
    frame_to_csv_bytes,
    provenance_json_bytes,
    software_version,
)
from spaceweather.ingestion.validate import (
    coerce_kp,
    mask_fill_values,
    parse_table,
    to_utc_series,
)
from spaceweather.models import DataBundle, SourceInfo


def test_parse_table_rejects_empty_and_skips_bad_rows() -> None:
    with pytest.raises(SchemaValidationError, match="non-empty"):
        parse_table([], source="test")
    records, issues = parse_table(
        [["time", "value"], ["2024-01-01", "1"], ["2024-01-02"], ["2024-01-03", "3"]],
        source="test",
    )
    assert records == [
        {"time": "2024-01-01", "value": "1"},
        {"time": "2024-01-03", "value": "3"},
    ]
    assert len(issues) == 1


def test_coerce_kp_masks_out_of_physical_range() -> None:
    values, invalid = coerce_kp(pd.Series([1.0, -1.0, 9.0, 9.5, "bad"]))
    assert values.iloc[0] == 1.0
    assert pd.isna(values.iloc[1])
    assert values.iloc[2] == 9.0
    assert pd.isna(values.iloc[3])
    assert pd.isna(values.iloc[4])
    assert invalid == 2


def test_to_utc_series_and_fill_masking() -> None:
    parsed = to_utc_series(["2024-01-01T00:00:00", "bad"])
    assert parsed.iloc[0] == pd.Timestamp("2024-01-01T00:00:00Z")
    assert pd.isna(parsed.iloc[1])
    masked = mask_fill_values(pd.Series([1.0, 999.9, -999.9, 10.0]), threshold=999.0)
    assert masked.iloc[0] == 1.0
    assert pd.isna(masked.iloc[1])
    assert pd.isna(masked.iloc[2])
    assert masked.iloc[3] == 10.0


def test_provenance_round_trip_and_csv_time_format() -> None:
    times = pd.date_range("2024-05-01", periods=3, freq="3h", tz="UTC")
    frame = pd.DataFrame(
        {
            "time_utc": times,
            "kp": [4.0, 5.0, 6.0],
        }
    )
    frame.attrs["units"] = {"kp": "unitless (0-9)"}
    source = SourceInfo(
        key="noaa_swpc",
        name="NOAA SWPC",
        url="https://example.test/kp.json",
        license="Public domain",
    )
    bundle = DataBundle(
        frame=frame,
        sources=[source],
        mode="live",
        is_sample=False,
        warnings=["Preliminary Kp."],
    )
    provenance = build_provenance(bundle, threshold=5.0, transformations=["Test transform."])
    assert provenance.time_window_utc is not None
    payload = provenance_json_bytes(provenance)
    decoded = json.loads(payload)
    assert decoded["notes"]["threshold_kp"] == 5.0
    assert decoded["notes"]["warnings"] == ["Preliminary Kp."]
    assert decoded["source_urls"] == ["https://example.test/kp.json"]
    assert "Test transform." in decoded["transformations"]
    assert "No interpolation" in " ".join(decoded["transformations"])
    assert software_version()

    csv_text = frame_to_csv_bytes(frame).decode("utf-8")
    assert "2024-05-01T00:00:00Z" in csv_text
    assert "2024-05-01T06:00:00Z" in csv_text
