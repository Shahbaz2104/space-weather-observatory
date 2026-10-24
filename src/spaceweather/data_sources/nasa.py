"""Optional NASA DONKI adapter for space-weather event metadata."""

from __future__ import annotations

from datetime import date

from spaceweather.attribution import NASA_DONKI
from spaceweather.config import Settings
from spaceweather.data_sources.base import make_source_info
from spaceweather.exceptions import SchemaValidationError, SourceUnavailableError
from spaceweather.ingestion.fetch import HttpClient
from spaceweather.models import DataStatus, SourceInfo


def fetch_donki_notifications(
    client: HttpClient,
    settings: Settings,
    *,
    start: date,
    end: date,
    notification_type: str = "all",
) -> tuple[list[dict[str, object]], SourceInfo]:
    """Fetch DONKI notifications when explicitly enabled.

    The default application does not depend on DONKI. A public ``DEMO_KEY`` is
    used only when ``SWO_NASA_ENABLED=true`` and no personal key is configured.
    """
    if not settings.nasa_enabled:
        raise SourceUnavailableError(
            "NASA DONKI is disabled. Set SWO_NASA_ENABLED=true to enable it."
        )
    api_key = settings.nasa_api_key or "DEMO_KEY"
    url = (
        f"{settings.donki_base_url}/notifications"
        f"?startDate={start.isoformat()}&endDate={end.isoformat()}"
        f"&type={notification_type}&api_key={api_key}"
    )
    result = client.fetch(url, ttl_seconds=settings.cache_ttl_seconds)
    payload = result.json()
    if not isinstance(payload, list):
        raise SchemaValidationError("DONKI response was not a JSON array")
    source = make_source_info(
        NASA_DONKI,
        retrieved_at=result.retrieved_at,
        stale=result.stale,
        from_cache=result.from_cache,
        status=DataStatus.OBSERVED,
        url=result.url,
    )
    return [dict(item) for item in payload if isinstance(item, dict)], source
