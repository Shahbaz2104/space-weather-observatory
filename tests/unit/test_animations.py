"""Animation sampling conventions."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from spaceweather.models import AnimationConfig
from spaceweather.visualization.animations import _prepare_observations


def test_frame_cap_is_respected_and_last_observation_is_kept(
    kp_frame_factory: Callable[..., pd.DataFrame],
) -> None:
    times = pd.date_range("2024-05-01", periods=100, freq="3h", tz="UTC")
    frame = kp_frame_factory([(str(timestamp), 5.0) for timestamp in times])

    for max_frames in (10, 12, 50, 100):
        sampled, stride, downsampled = _prepare_observations(
            frame, AnimationConfig(max_frames=max_frames)
        )
        assert len(sampled) <= max_frames
        assert sampled["time_utc"].iloc[-1] == frame["time_utc"].iloc[-1]
        assert downsampled is (stride > 1)


def test_requested_stride_is_never_reduced(
    kp_frame_factory: Callable[..., pd.DataFrame],
) -> None:
    times = pd.date_range("2024-05-01", periods=100, freq="3h", tz="UTC")
    frame = kp_frame_factory([(str(timestamp), 5.0) for timestamp in times])

    sampled, stride, _ = _prepare_observations(
        frame, AnimationConfig(max_frames=600, frame_stride=10)
    )

    assert stride == 10
    assert len(sampled) == 11
    assert sampled["time_utc"].iloc[-1] == frame["time_utc"].iloc[-1]
