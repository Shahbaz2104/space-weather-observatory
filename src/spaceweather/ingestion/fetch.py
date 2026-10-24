"""HTTP client with bounded retries, timeouts, and stale-cache fallback."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from spaceweather import __version__
from spaceweather.config import Settings
from spaceweather.exceptions import (
    OfflineModeError,
    SchemaValidationError,
    SourceUnavailableError,
)
from spaceweather.ingestion.cache import CacheHit, FileCache
from spaceweather.logging_config import get_logger

logger = get_logger("fetch")

RETRY_STATUS_CODES = (408, 429, 500, 502, 503, 504)
USER_AGENT = (
    f"SpaceWeatherObservatory/{__version__} "
    "(educational scientific visualization; contact via repository)"
)


@dataclass(frozen=True)
class FetchResult:
    """Raw response bytes plus provenance."""

    content: bytes
    url: str
    retrieved_at: datetime
    from_cache: bool
    stale: bool
    content_type: str = ""

    def json(self) -> Any:
        """Decode the response as JSON with a helpful validation error."""
        try:
            return json.loads(self.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SchemaValidationError(
                f"Response from {self.url} was not valid JSON: {exc}"
            ) from exc

    def text(self) -> str:
        """Decode the response as UTF-8 text."""
        try:
            return self.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SchemaValidationError(
                f"Response from {self.url} was not valid UTF-8: {exc}"
            ) from exc


class HttpClient:
    """Requests session configured for scientific data endpoints."""

    def __init__(self, settings: Settings, cache: FileCache | None = None) -> None:
        self.settings = settings
        self.cache = cache
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": USER_AGENT, "Accept": "application/json,text/plain,*/*"}
        )
        retry = Retry(
            total=settings.http_retries,
            connect=settings.http_retries,
            read=settings.http_retries,
            status=settings.http_retries,
            backoff_factor=settings.http_backoff_factor,
            status_forcelist=RETRY_STATUS_CODES,
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=8)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def fetch(self, url: str, *, ttl_seconds: int) -> FetchResult:
        """Fetch a URL using the cache and explicit offline/stale semantics."""
        hit: CacheHit | None = None
        if self.cache is not None:
            hit = self.cache.read(url, ttl_seconds=ttl_seconds)
            if hit is not None and not hit.stale:
                logger.debug("Fresh cache hit for %s", url)
                return FetchResult(
                    content=hit.content,
                    url=url,
                    retrieved_at=hit.retrieved_at,
                    from_cache=True,
                    stale=False,
                    content_type=hit.content_type,
                )

        if self.settings.offline_mode:
            if hit is not None:
                logger.info("Offline mode: returning cached response for %s", url)
                return self._from_hit(hit, url)
            raise OfflineModeError(
                f"Offline mode is enabled and no cached response exists for {url}"
            )

        try:
            response = self.session.get(
                url,
                timeout=self.settings.http_timeout_seconds,
                allow_redirects=True,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            if hit is not None:
                logger.warning(
                    "Source %s failed (%s); returning stale cache from %s",
                    url,
                    exc,
                    hit.retrieved_at.isoformat(),
                )
                return self._from_hit(hit, url)
            raise SourceUnavailableError(f"Could not retrieve {url}: {exc}") from exc

        content_type = response.headers.get("Content-Type", "")
        retrieved_at = datetime.now(UTC)
        if self.cache is not None:
            self.cache.write(url, response.content, content_type=content_type)
        return FetchResult(
            content=response.content,
            url=url,
            retrieved_at=retrieved_at,
            from_cache=False,
            stale=False,
            content_type=content_type,
        )

    def _from_hit(self, hit: CacheHit, url: str) -> FetchResult:
        return FetchResult(
            content=hit.content,
            url=url,
            retrieved_at=hit.retrieved_at,
            from_cache=True,
            stale=True,
            content_type=hit.content_type,
        )

    def close(self) -> None:
        """Close the underlying session."""
        self.session.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
