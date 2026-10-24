"""Storm-run detection, duration, and G-scale conventions."""

from __future__ import annotations

import pandas as pd
import pytest

from spaceweather.processing.events import (
    detect_events,
    events_to_frame,
    kp_to_g_scale,
)


@pytest.mark.parametrize(
    ("kp", "expected"),
    [(4.99, None), (5.0, "G1"), (6.0, "G2"), (7.0, "G3"), (8.0, "G4"), (9.0, "G5")],
)
def test_g_scale_bands(kp: float, expected: str | None) -> None:
    assert kp_to_g_scale(kp) == expected


def test_detects_contiguous_run_with_sampled_duration(kp_frame_factory) -> None:
    frame = kp_frame_factory(
        [
            ("2024-05-10T00:00:00", 4.0),
            ("2024-05-10T03:00:00", 5.0),
            ("2024-05-10T06:00:00", 6.0),
            ("2024-05-10T09:00:00", 5.5),
            ("2024-05-10T12:00:00", 4.5),
        ]
    )
    events = detect_events(frame, threshold=5.0)
    assert len(events) == 1
    event = events[0]
    assert event.start_utc == pd.Timestamp("2024-05-10T03:00:00Z").to_pydatetime()
    assert event.end_utc == pd.Timestamp("2024-05-10T12:00:00Z").to_pydatetime()
    assert event.duration_hours == 9.0
    assert event.sample_count == 3
    assert event.peak_kp == 6.0
    assert event.missing_samples == 0
    assert event.g_scale == "G2"


def test_one_missing_slot_is_allowed_inside_run(kp_frame_factory) -> None:
    frame = kp_frame_factory(
        [
            ("2024-05-10T00:00:00", 5.0),
            ("2024-05-10T03:00:00", 6.0),
            ("2024-05-10T09:00:00", 5.5),
            ("2024-05-10T12:00:00", 4.0),
        ]
    )
    events = detect_events(frame, threshold=5.0)
    assert len(events) == 1
    assert events[0].missing_samples == 1
    assert events[0].sample_count == 3


def test_two_missing_slots_break_the_run(kp_frame_factory) -> None:
    frame = kp_frame_factory(
        [
            ("2024-05-10T00:00:00", 5.0),
            ("2024-05-10T03:00:00", 6.0),
            ("2024-05-10T12:00:00", 5.5),
            ("2024-05-10T15:00:00", 4.0),
        ]
    )
    events = detect_events(frame, threshold=5.0)
    assert len(events) == 2
    assert [event.duration_hours for event in events] == [6.0, 3.0]


def test_empty_and_below_threshold_frames(kp_frame_factory) -> None:
    empty = kp_frame_factory([])
    assert detect_events(empty, threshold=5.0) == []
    quiet = kp_frame_factory(
        [("2024-05-10T00:00:00", 2.0), ("2024-05-10T03:00:00", 3.0)]
    )
    assert detect_events(quiet, threshold=5.0) == []
    assert events_to_frame([]).empty


def test_events_to_frame_has_expected_columns(kp_frame_factory) -> None:
    frame = kp_frame_factory([("2024-05-10T00:00:00", 7.0)])
    table = events_to_frame(detect_events(frame, threshold=5.0))
    assert list(table.columns) == [
        "start_utc",
        "end_utc",
        "duration_hours",
        "peak_kp",
        "mean_kp",
        "sample_count",
        "expected_samples",
        "missing_samples",
        "threshold",
        "status",
        "source",
        "g_scale",
    ]
