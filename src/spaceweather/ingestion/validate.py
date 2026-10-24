"""Reusable parsing and validation helpers for tabular source payloads."""

from __future__ import annotations

from typing import Any

import pandas as pd

from spaceweather.exceptions import SchemaValidationError


def parse_table(payload: object, *, source: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Normalize a list-of-dicts or header-plus-rows payload into records."""
    if not isinstance(payload, list) or not payload:
        raise SchemaValidationError(f"{source}: expected a non-empty JSON array")
    issues: list[str] = []
    if all(isinstance(item, dict) for item in payload):
        return [dict(item) for item in payload], issues
    if isinstance(payload[0], list):
        header = payload[0]
        if not header or not all(isinstance(name, str) for name in header):
            raise SchemaValidationError(f"{source}: first row is not a string header")
        records: list[dict[str, Any]] = []
        for index, row in enumerate(payload[1:], start=1):
            if not isinstance(row, list) or len(row) != len(header):
                issues.append(f"row {index} has an unexpected shape and was skipped")
                continue
            records.append(dict(zip(header, row, strict=True)))
        if not records:
            raise SchemaValidationError(f"{source}: no data rows after the header")
        return records, issues
    raise SchemaValidationError(f"{source}: unsupported JSON table layout")


def to_utc_series(values: pd.Series | list[object]) -> pd.Series:
    """Convert timestamps to timezone-aware UTC, preserving invalid values as NaT."""
    series = pd.Series(values)
    parsed = pd.to_datetime(series, utc=True, errors="coerce", format="mixed")
    return pd.Series(parsed, index=series.index)


def coerce_numeric(series: pd.Series) -> pd.Series:
    """Coerce a column to float, turning unparseable values into NaN."""
    return pd.to_numeric(series, errors="coerce").astype("float64")


def coerce_kp(series: pd.Series) -> tuple[pd.Series, int]:
    """Coerce Kp values and mask values outside the physical 0-9 range."""
    numeric = coerce_numeric(series)
    invalid = numeric.notna() & ((numeric < 0.0) | (numeric > 9.0))
    invalid_count = int(invalid.sum())
    return numeric.mask(invalid), invalid_count


def require_columns(frame: pd.DataFrame, columns: list[str], *, source: str) -> None:
    """Raise when required columns are absent."""
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise SchemaValidationError(
            f"{source}: missing required columns: {', '.join(missing)}"
        )


def mask_fill_values(series: pd.Series, *, threshold: float) -> pd.Series:
    """Mask the positive fill values used by OMNI-style flat files."""
    numeric = coerce_numeric(series)
    return numeric.mask(numeric.abs() >= threshold)
