"""Transparent storm-interval detection with explicit conventions."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from spaceweather.models import StormEvent
from spaceweather.processing.cleaning import KP_CADENCE_HOURS, valid_kp

G_SCALE_THRESHOLDS = (
    (9.0, "G5"),
    (8.0, "G4"),
    (7.0, "G3"),
    (6.0, "G2"),
    (5.0, "G1"),
)


def kp_to_g_scale(kp: float) -> str | None:
    """Map a Kp value to the NOAA G-scale category (Kp 5 = G1)."""
    for threshold, label in G_SCALE_THRESHOLDS:
        if kp >= threshold:
            return label
    return None


def detect_events(
    frame: pd.DataFrame,
    *,
    threshold: float = 5.0,
    cadence_hours: float = KP_CADENCE_HOURS,
    max_gap_hours: float | None = None,
) -> list[StormEvent]:
    """Detect contiguous runs of observations at or above ``threshold``.

    A run continues across gaps of at most ``max_gap_hours`` (default: two
    cadence steps) so that a single missing slot is counted as missing inside
    the event rather than silently splitting or shrinking it.
    """
    valid = valid_kp(frame)
    if valid.empty:
        return []
    if max_gap_hours is None:
        max_gap_hours = cadence_hours * 2.0

    ordered = valid.sort_values("time_utc")
    times = list(pd.to_datetime(ordered["time_utc"], utc=True))
    values = list(ordered["kp"].astype(float))
    statuses = list(ordered["status"].astype(str))
    sources = list(ordered["source"].astype(str))

    runs: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    previous_time: pd.Timestamp | None = None

    def flush() -> None:
        nonlocal current
        if current is not None:
            runs.append(current)
            current = None

    for timestamp, value, status, source in zip(
        times, values, statuses, sources, strict=True
    ):
        qualifies = value >= threshold
        gap_break = (
            previous_time is not None
            and (timestamp - previous_time) > timedelta(hours=max_gap_hours)
        )
        if not qualifies:
            flush()
            previous_time = timestamp
            continue
        if current is None or gap_break:
            flush()
            current = {
                "times": [timestamp],
                "values": [value],
                "statuses": [status],
                "sources": [source],
            }
        else:
            assert current is not None
            times_list = current["times"]
            values_list = current["values"]
            statuses_list = current["statuses"]
            sources_list = current["sources"]
            assert isinstance(times_list, list)
            assert isinstance(values_list, list)
            assert isinstance(statuses_list, list)
            assert isinstance(sources_list, list)
            times_list.append(timestamp)
            values_list.append(value)
            statuses_list.append(status)
            sources_list.append(source)
        previous_time = timestamp
    flush()

    events: list[StormEvent] = []
    for run in runs:
        run_times = run["times"]
        run_values = run["values"]
        run_statuses = run["statuses"]
        run_sources = run["sources"]
        assert isinstance(run_times, list)
        assert isinstance(run_values, list)
        assert isinstance(run_statuses, list)
        assert isinstance(run_sources, list)
        start = run_times[0]
        last = run_times[-1]
        end = last + timedelta(hours=cadence_hours)
        duration_hours = (end - start).total_seconds() / 3600.0
        expected = max(1, round(duration_hours / cadence_hours))
        missing = max(0, expected - len(run_times))
        status = (
            "definitive"
            if all(value == "definitive" for value in run_statuses)
            else "preliminary"
            if "preliminary" in run_statuses
            else run_statuses[0]
        )
        unique_sources = sorted(set(run_sources))
        events.append(
            StormEvent(
                start_utc=start.to_pydatetime(),
                end_utc=end.to_pydatetime(),
                duration_hours=duration_hours,
                peak_kp=max(run_values),
                mean_kp=sum(run_values) / len(run_values),
                sample_count=len(run_times),
                expected_samples=expected,
                missing_samples=missing,
                threshold=threshold,
                status=status,
                source=", ".join(unique_sources),
                g_scale=kp_to_g_scale(max(run_values)),
            )
        )
    return events


def events_to_frame(events: list[StormEvent]) -> pd.DataFrame:
    """Convert detected events into a presentation-friendly dataframe."""
    if not events:
        return pd.DataFrame(
            columns=[
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
        )
    return pd.DataFrame([event.model_dump() for event in events])


def storm_intervals(
    frame: pd.DataFrame, *, threshold: float = 5.0
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Return start/end pairs suitable for chart shading."""
    events = detect_events(frame, threshold=threshold)
    return [
        (pd.Timestamp(event.start_utc), pd.Timestamp(event.end_utc)) for event in events
    ]


def event_matches_detected_count(
    events: list[StormEvent], *, threshold: float
) -> int:
    """Count events whose peak meets the official G1 threshold."""
    return sum(1 for event in events if event.peak_kp >= threshold)
