"""Project-specific exceptions."""

from __future__ import annotations


class SpaceWeatherError(Exception):
    """Base class for all application errors."""


class SourceError(SpaceWeatherError):
    """A data source could not be used."""


class SourceUnavailableError(SourceError):
    """A data source failed and no usable cache entry exists."""


class OfflineModeError(SourceError):
    """A network request was attempted while offline mode is enabled."""


class SchemaValidationError(SourceError):
    """A source response did not match the expected schema."""

    def __init__(self, message: str, issues: list[str] | None = None) -> None:
        super().__init__(message)
        self.issues = issues or []


class InsufficientDataError(SpaceWeatherError):
    """An analysis needs more valid observations than are available."""
