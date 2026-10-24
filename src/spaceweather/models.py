"""Typed records shared across ingestion, analysis, and presentation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, Field, field_validator


class DataStatus(StrEnum):
    """Provenance status of a measurement or source."""

    OBSERVED = "observed"
    PRELIMINARY = "preliminary"
    DEFINITIVE = "definitive"
    ESTIMATED = "estimated"
    FORECAST = "forecast"
    UNKNOWN = "unknown"


class Attribution(BaseModel):
    """Static attribution metadata for a data provider."""

    key: str
    name: str
    url: str
    license: str
    citation: str


class SourceInfo(BaseModel):
    """Runtime state of a source used to build a result."""

    key: str
    name: str
    url: str
    license: str = ""
    citation: str = ""
    retrieved_at: datetime | None = None
    stale: bool = False
    from_cache: bool = False
    status: DataStatus = DataStatus.UNKNOWN


class ValidationIssue(BaseModel):
    """A structured data-quality finding."""

    level: Literal["info", "warning", "error"]
    message: str
    count: int = 1


class StormEvent(BaseModel):
    """A contiguous run of storm-threshold Kp observations.

    ``duration_hours`` spans the sampled three-hour intervals. It is not the
    physical duration of the underlying geomagnetic disturbance.
    """

    start_utc: datetime
    end_utc: datetime
    duration_hours: float
    peak_kp: float
    mean_kp: float
    sample_count: int
    expected_samples: int
    missing_samples: int
    threshold: float
    status: str
    source: str
    g_scale: str | None = None


class AnimationConfig(BaseModel):
    """Deterministic rendering settings for an animation export."""

    fps: int = Field(default=24, ge=1, le=60)
    frame_stride: int = Field(default=1, ge=1)
    width: float = Field(default=15.0, gt=0.0)
    height: float = Field(default=8.0, gt=0.0)
    dpi: int = Field(default=110, ge=50, le=300)
    max_frames: int = Field(default=600, ge=10)
    seed: int = Field(default=42, ge=0)
    threshold: float = Field(default=5.0, ge=0.0, le=9.0)


class Provenance(BaseModel):
    """Reproducibility metadata attached to exports."""

    project: str = "Space Weather Observatory"
    software_version: str
    created_at: datetime
    source_urls: list[str] = Field(default_factory=list)
    retrieved_at: list[datetime] = Field(default_factory=list)
    time_window_utc: tuple[datetime, datetime] | None = None
    units: dict[str, str] = Field(default_factory=dict)
    transformations: list[str] = Field(default_factory=list)
    missing_data_policy: str = (
        "Missing or rejected observations are preserved as missing and are never "
        "replaced with zero."
    )
    animation: AnimationConfig | None = None
    notes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("software_version")
    @classmethod
    def _non_empty_version(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("software_version must not be empty")
        return value


@dataclass
class DataBundle:
    """A dataframe plus the provenance needed to describe it honestly."""

    frame: pd.DataFrame
    sources: list[SourceInfo] = field(default_factory=list)
    mode: str = "auto"
    is_sample: bool = False
    message: str = ""
    last_updated: datetime | None = None
    timezone: str = "UTC"
    warnings: list[str] = field(default_factory=list)
