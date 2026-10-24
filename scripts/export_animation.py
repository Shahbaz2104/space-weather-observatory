"""Export the static overview and an observed-Kp animation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from spaceweather.cli import animate_main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(animate_main())
