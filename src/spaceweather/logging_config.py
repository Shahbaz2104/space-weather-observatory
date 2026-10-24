"""Consistent logging setup for the application and command-line tools."""

from __future__ import annotations

import logging
import sys


def configure_logging(level: str | int = "INFO", force: bool = False) -> None:
    """Configure root logging once, writing to stderr."""
    if isinstance(level, str):
        numeric_level = getattr(logging, level.upper(), logging.INFO)
    else:
        numeric_level = level
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        stream=sys.stderr,
        force=force,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger."""
    return logging.getLogger(f"spaceweather.{name}")
