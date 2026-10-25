"""Console entry points for dataset building and animation export."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from spaceweather.config import get_settings
from spaceweather.datasets import build_samples
from spaceweather.exceptions import SourceError
from spaceweather.ingestion.cache import FileCache
from spaceweather.ingestion.samples import load_sample_kp
from spaceweather.logging_config import configure_logging
from spaceweather.models import AnimationConfig
from spaceweather.services import load_kp_window, load_noaa_bundle
from spaceweather.visualization.animations import (
    encoder_available,
    render_animation,
    save_kp_overview_png,
)


def fetch_main(argv: list[str] | None = None) -> int:
    """Rebuild the versioned sample, processed dataset, and metadata."""
    parser = argparse.ArgumentParser(
        prog="swo-fetch",
        description=(
            "Download NOAA, GFZ, and NASA sources; rebuild data/processed and the "
            "versioned offline sample."
        ),
    )
    parser.add_argument(
        "--skip-processed",
        action="store_true",
        help="Only rebuild the committed sample, not the processed parquet.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Clear the HTTP cache before building.",
    )
    args = parser.parse_args(argv)

    configure_logging()
    settings = get_settings()
    if args.refresh:
        removed = FileCache(settings.cache_dir).clear()
        print(f"Cleared {removed} cached response file(s).")
    try:
        result = build_samples(settings, write_processed=not args.skip_processed)
    except SourceError as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1

    print(f"Kp 2003 : {result.rows_2003:,} rows")
    print(f"Kp 2024 : {result.rows_2024:,} rows")
    print(f"OMNI    : {result.rows_solar_wind:,} rows")
    print(f"Metadata: {result.metadata_path}")
    if result.processed_path is not None:
        print(f"Processed: {result.processed_path}")
    print("Note: bundled data are genuine observations, not live telemetry.")
    return 0


def _parse_bound(value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    return timestamp


def animate_main(argv: list[str] | None = None) -> int:
    """Export the static overview and an observed-Kp animation."""
    parser = argparse.ArgumentParser(
        prog="swo-animate",
        description="Export a static Kp overview and a deterministic animation.",
    )
    parser.add_argument(
        "--format", choices=["gif", "mp4"], default="gif", help="Animation container."
    )
    parser.add_argument("--fps", type=int, default=6, help="Frames per second.")
    parser.add_argument(
        "--threshold", type=float, default=5.0, help="Storm threshold on the Kp scale."
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use the bundled genuine-data sample instead of the network.",
    )
    parser.add_argument(
        "--live-only",
        action="store_true",
        help="Fail instead of falling back when a live source is unavailable.",
    )
    parser.add_argument("--start", help="UTC start, e.g. 2024-05-01.")
    parser.add_argument("--end", help="UTC end (inclusive date), e.g. 2024-05-31.")
    parser.add_argument("--output", help="Animation output path.")
    parser.add_argument(
        "--no-png", action="store_true", help="Skip the static overview PNG."
    )
    args = parser.parse_args(argv)

    if (args.start is None) != (args.end is None):
        parser.error("--start and --end must be provided together")
    if args.threshold < 0 or args.threshold > 9:
        parser.error("--threshold must be between 0 and 9")
    if args.fps < 1 or args.fps > 60:
        parser.error("--fps must be between 1 and 60")

    configure_logging()
    settings = get_settings()
    settings.ensure_directories()
    mode = "offline" if args.offline else ("live" if args.live_only else "auto")

    try:
        if args.start and args.end:
            start = _parse_bound(args.start)
            end = _parse_bound(args.end)
            if start is None or end is None:
                parser.error("Could not parse --start/--end")
            if len(str(args.end)) == 10:
                end = end + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            bundle = load_kp_window(mode, start=start, end=end, settings=settings)
        elif mode == "offline":
            bundle = load_sample_kp(settings)
            bundle.warnings.append("Offline mode requested on the command line.")
        else:
            try:
                bundle = load_noaa_bundle(settings)
                if bundle.frame.empty:
                    raise SourceError("NOAA returned no observations")
            except SourceError as exc:
                if mode == "live":
                    raise
                bundle = load_sample_kp(settings)
                bundle.warnings.append(f"Live source unavailable: {exc}")
    except SourceError as exc:
        print(f"Data unavailable: {exc}", file=sys.stderr)
        return 1

    if len(bundle.frame) < 2:
        print("No usable observations were found; nothing to render.", file=sys.stderr)
        return 1

    fmt = args.format
    if not encoder_available(fmt):
        print(f"{fmt.upper()} encoder unavailable; falling back to GIF.", file=sys.stderr)
        fmt = "gif"

    source_label = (
        "SAMPLED · GFZ KP (OFFLINE)" if bundle.is_sample else "OBSERVED · NOAA SWPC"
    )
    config = AnimationConfig(
        fps=max(1, args.fps),
        max_frames=settings.max_animation_frames,
        threshold=args.threshold,
        width=15.0,
        height=8.0,
        dpi=110,
    )
    animation_path = (
        Path(args.output)
        if args.output
        else settings.output_dir / f"geomagnetic_story.{fmt}"
    )
    png_path = settings.output_dir / "geomagnetic_overview.png"

    if not args.no_png:
        save_kp_overview_png(
            bundle.frame,
            png_path,
            threshold=args.threshold,
            source_label=source_label,
        )
        print(f"Overview  : {png_path}")

    result = render_animation(
        bundle.frame,
        animation_path,
        fmt=fmt,
        config=config,
        source_label=source_label,
    )

    print(f"Animation : {animation_path}")
    print(
        f"Frames    : {result['frames']} at {result['fps']} fps "
        f"({result['duration_seconds']:.1f} s)"
    )
    print(
        f"Observed  : {len(bundle.frame)} rows · "
        f"{bundle.frame['time_utc'].min()} to {bundle.frame['time_utc'].max()} UTC"
    )
    for warning in bundle.warnings:
        print(f"Warning   : {warning}")
    print("Timezone  : UTC")
    print("Note      : Cached or sampled data are labelled; not a forecast.")
    return 0
