"""Small, dependency-free HTTP response cache with explicit staleness."""

from __future__ import annotations

import contextlib
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from spaceweather.logging_config import get_logger

logger = get_logger("cache")


@dataclass(frozen=True)
class CacheHit:
    """A cached response and its age metadata."""

    content: bytes
    retrieved_at: datetime
    content_type: str = ""
    stale: bool = False


class FileCache:
    """Content-addressed on-disk cache for source responses."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _paths(self, url: str) -> tuple[Path, Path]:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        return self.root / f"{digest}.bin", self.root / f"{digest}.json"

    def read(self, url: str, ttl_seconds: int) -> CacheHit | None:
        """Return a cached response, or ``None`` when nothing readable exists."""
        data_path, meta_path = self._paths(url)
        if not data_path.exists() or not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            retrieved_at = datetime.fromisoformat(meta["retrieved_at"])
            if retrieved_at.tzinfo is None:
                retrieved_at = retrieved_at.replace(tzinfo=UTC)
            content = data_path.read_bytes()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Ignoring unreadable cache entry for %s: %s", url, exc)
            return None
        age = datetime.now(UTC) - retrieved_at
        stale = ttl_seconds >= 0 and age > timedelta(seconds=ttl_seconds)
        return CacheHit(
            content=content,
            retrieved_at=retrieved_at,
            content_type=str(meta.get("content_type", "")),
            stale=stale,
        )

    def write(self, url: str, content: bytes, content_type: str = "") -> datetime:
        """Write a response and return its retrieval timestamp."""
        data_path, meta_path = self._paths(url)
        retrieved_at = datetime.now(UTC)
        meta = {
            "url": url,
            "retrieved_at": retrieved_at.isoformat(),
            "content_type": content_type,
            "bytes": len(content),
        }
        data_tmp = data_path.with_suffix(".bin.tmp")
        meta_tmp = meta_path.with_suffix(".json.tmp")
        try:
            data_tmp.write_bytes(content)
            meta_tmp.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            data_tmp.replace(data_path)
            meta_tmp.replace(meta_path)
        except OSError as exc:
            logger.warning("Could not write cache entry for %s: %s", url, exc)
        return retrieved_at

    def clear(self) -> int:
        """Delete every cached entry and return the number of data files removed."""
        removed = 0
        for path in self.root.glob("*.bin"):
            try:
                path.unlink()
                removed += 1
            except OSError:
                pass
        for path in self.root.glob("*.json"):
            with contextlib.suppress(OSError):
                path.unlink()
        return removed
