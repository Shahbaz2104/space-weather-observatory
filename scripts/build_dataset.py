"""Build the combined processed Kp dataset from GFZ and NOAA."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from spaceweather.config import get_settings  # noqa: E402
from spaceweather.data_sources.historical import fetch_gfz_kp  # noqa: E402
from spaceweather.data_sources.noaa import fetch_recent_kp  # noqa: E402
from spaceweather.ingestion.cache import FileCache  # noqa: E402
from spaceweather.ingestion.fetch import HttpClient  # noqa: E402
from spaceweather.logging_config import configure_logging  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=None,
        help="Output parquet path (default: data/processed/kp_combined.parquet).",
    )
    args = parser.parse_args()

    configure_logging()
    settings = get_settings()
    settings.ensure_directories()
    with HttpClient(settings, cache=FileCache(settings.cache_dir)) as client:
        gfz_frame, _ = fetch_gfz_kp(client, settings)
        recent_frame, _ = fetch_recent_kp(client, settings)

    combined = pd.concat([gfz_frame, recent_frame], ignore_index=True)
    combined = combined.sort_values("time_utc").drop_duplicates(
        "time_utc", keep="last"
    )
    output = Path(args.output) if args.output else settings.processed_dir / "kp_combined.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(output, index=False)
    print(f"Wrote {len(combined):,} rows to {output}")
    print(
        f"Range: {combined['time_utc'].min()} to {combined['time_utc'].max()} UTC"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
