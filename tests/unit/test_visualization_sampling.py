"""Render-time sampling must bound chart points without hiding events or gaps."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from spaceweather.visualization.distributions import scatter_figure
from spaceweather.visualization.timeseries import kp_timeline_figure, solar_wind_figure


def _long_kp_frame(
    factory: Callable[..., pd.DataFrame], *, missing_at: int | None = None
) -> pd.DataFrame:
    times = pd.date_range("2020-01-01T00:00:00Z", periods=1_001, freq="3h")
    rows = [
        (timestamp.isoformat(), 9.0 if index == 505 else 4.0)
        for index, timestamp in enumerate(times)
    ]
    frame = factory(rows)
    if missing_at is not None:
        frame.loc[missing_at, "kp"] = np.nan
    return frame


def test_kp_timeline_samples_the_trace_but_keeps_the_peak_and_events(
    kp_frame_factory: Callable[..., pd.DataFrame],
) -> None:
    frame = _long_kp_frame(kp_frame_factory)
    figure = kp_timeline_figure(frame, threshold=5.0, max_points=100)

    observation = next(trace for trace in figure.data if trace.name == "Kp observation")
    peak = next(trace for trace in figure.data if trace.name.startswith("Peak"))

    assert len(observation.x) < len(frame)
    assert len(observation.x) <= 102
    assert pd.Timestamp(peak.x[0]) == pd.Timestamp("2020-01-01T00:00:00Z") + pd.Timedelta(
        hours=505 * 3
    )
    assert peak.y[0] == 9.0
    assert len(figure.layout.shapes) >= 1
    assert figure.layout.meta["downsample_rows_total"] == len(frame)
    assert figure.layout.meta["downsample_rows_displayed"] == len(observation.x)
    assert "downsample_note" in figure.layout.meta


def test_kp_timeline_keeps_missing_data_as_a_visible_gap(
    kp_frame_factory: Callable[..., pd.DataFrame],
) -> None:
    frame = _long_kp_frame(kp_frame_factory, missing_at=500)
    figure = kp_timeline_figure(frame, threshold=5.0, max_points=100)

    observation = next(trace for trace in figure.data if trace.name == "Kp observation")
    assert observation.connectgaps is False
    assert np.isnan(np.asarray(observation.y, dtype=float)).any()


def test_solar_wind_samples_the_wind_traces_but_not_the_kp_overlay(
    kp_frame_factory: Callable[..., pd.DataFrame],
) -> None:
    times = pd.date_range("2024-05-01T00:00:00Z", periods=10_000, freq="1min")
    wind = pd.DataFrame(
        {
            "time_utc": times,
            "speed_kms": 400.0,
            "density_cm3": 5.0,
            "bz_gsm_nt": -2.0,
            "bt_nt": 8.0,
        }
    )
    kp = kp_frame_factory(
        [("2024-05-01T00:00:00", 4.0), ("2024-05-01T03:00:00", 5.0)]
    )
    figure = solar_wind_figure(wind, kp=kp, max_points=1_000)

    speed = next(trace for trace in figure.data if trace.name == "Speed")
    kp_trace = next(trace for trace in figure.data if trace.name == "Kp")

    assert len(speed.x) < len(wind)
    assert len(speed.x) <= 1_002
    assert len(kp_trace.x) == len(kp)
    assert figure.layout.meta["downsample_rows_total"] == len(wind)
    assert "downsample_note" in figure.layout.meta


def test_scatter_samples_points_without_changing_the_caller_frame() -> None:
    frame = pd.DataFrame(
        {
            "time_utc": pd.date_range("2024-05-01T00:00:00Z", periods=10_000, freq="1min"),
            "speed_kms": np.linspace(300.0, 800.0, 10_000),
            "kp": np.linspace(0.0, 9.0, 10_000),
        }
    )
    original_rows = len(frame)
    figure = scatter_figure(
        frame,
        x="speed_kms",
        y="kp",
        x_label="Speed (km/s)",
        y_label="Kp",
        title="Speed versus Kp",
        max_points=1_000,
    )

    assert len(figure.data[0].x) < original_rows
    assert len(figure.data[0].x) <= 1_002
    assert len(frame) == original_rows
    assert figure.layout.meta["downsample_rows_total"] == original_rows
    assert "downsample_note" in figure.layout.meta
