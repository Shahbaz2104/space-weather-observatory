"""Shared fixtures for the test suite."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pandas as pd
import pytest


@pytest.fixture
def kp_frame_factory() -> Callable[..., pd.DataFrame]:
    """Build a canonical Kp dataframe from (timestamp, value) pairs."""

    def make(
        rows: list[tuple[str, float | None]],
        *,
        source: str = "test",
        status: str = "definitive",
    ) -> pd.DataFrame:
        records = []
        for timestamp, value in rows:
            records.append(
                {
                    "time_utc": pd.Timestamp(timestamp, tz="UTC"),
                    "kp": value,
                    "a_running": pd.NA,
                    "station_count": pd.NA,
                    "source": source,
                    "status": status,
                    "is_missing": value is None,
                }
            )
        if not records:
            return pd.DataFrame(
                {
                    "time_utc": pd.Series(dtype="datetime64[ns, UTC]"),
                    "kp": pd.Series(dtype="float64"),
                    "a_running": pd.Series(dtype="Int64"),
                    "station_count": pd.Series(dtype="Int64"),
                    "source": pd.Series(dtype="object"),
                    "status": pd.Series(dtype="object"),
                    "is_missing": pd.Series(dtype="bool"),
                }
            )
        frame = pd.DataFrame.from_records(records)
        frame["time_utc"] = pd.to_datetime(frame["time_utc"], utc=True)
        frame["kp"] = pd.to_numeric(frame["kp"], errors="coerce")
        frame["a_running"] = pd.array(frame["a_running"], dtype="Int64")
        frame["station_count"] = pd.array(frame["station_count"], dtype="Int64")
        frame["is_missing"] = frame["is_missing"].astype(bool)
        return frame

    return make


@pytest.fixture
def utc_timestamp() -> Callable[[datetime], pd.Timestamp]:
    """Coerce a datetime to a UTC pandas timestamp."""

    def make(value: datetime) -> pd.Timestamp:
        timestamp = pd.Timestamp(value)
        return timestamp if timestamp.tzinfo else timestamp.tz_localize("UTC")

    return make
