"""Quickstart: fetch the latest NOAA Kp observations and render a data story.

Outputs:
  output/geomagnetic_overview.png
  output/geomagnetic_story.gif   (or .mp4 with --format mp4)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from spaceweather.config import get_settings  # noqa: E402
from spaceweather.exceptions import SourceError  # noqa: E402
from spaceweather.ingestion.samples import load_sample_kp  # noqa: E402
from spaceweather.logging_config import configure_logging, get_logger  # noqa: E402
from spaceweather.models import AnimationConfig, DataBundle  # noqa: E402
from spaceweather.services import load_noaa_bundle  # noqa: E402
from spaceweather.visualization.animations import (  # noqa: E402
    encoder_available,
    render_animation,
    save_kp_overview_png,
)

logger = get_logger("quickstart")


def _load_bundle() -> DataBundle:
    settings = get_settings()
    try:
        bundle = load_noaa_bundle(settings)
        if bundle.frame.empty:
            raise SourceError("NOAA returned no observations")
        return bundle
    except SourceError as exc:
        logger.warning("Live source unavailable (%s); using the bundled sample", exc)
        bundle = load_sample_kp(settings)
        bundle.warnings.append(f"Live source unavailable: {exc}")
        return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=["gif", "mp4"],
        default="gif",
        help="Animation container (GIF is the dependency-free fallback).",
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
    args = parser.parse_args()

    configure_logging()
    settings = get_settings()
    settings.ensure_directories()

    if args.offline:
        bundle = load_sample_kp(settings)
        bundle.warnings.append("Offline mode requested on the command line.")
    else:
        bundle = _load_bundle()

    if len(bundle.frame) < 2:
        print("No usable observations were found; nothing to render.", file=sys.stderr)
        return 1

    fmt = args.format
    if not encoder_available(fmt):
        fallback = "gif"
        logger.warning("%s encoder unavailable; falling back to %s", fmt, fallback)
        fmt = fallback

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

    png_path = settings.output_dir / "geomagnetic_overview.png"
    animation_path = settings.output_dir / f"geomagnetic_story.{fmt}"

    save_kp_overview_png(
        bundle.frame,
        png_path,
        threshold=args.threshold,
        source_label=source_label,
    )
    result = render_animation(
        bundle.frame,
        animation_path,
        fmt=fmt,
        config=config,
        source_label=source_label,
    )

    print(f"Overview   : {png_path}")
    print(f"Animation  : {animation_path}")
    print(
        f"Frames     : {result['frames']} at {result['fps']} fps "
        f"({result['duration_seconds']:.1f} s)"
    )
    print(
        f"Observations: {len(bundle.frame)} · "
        f"{bundle.frame['time_utc'].min()} to {bundle.frame['time_utc'].max()} UTC"
    )
    for warning in bundle.warnings:
        print(f"Warning    : {warning}")
    print("Timezone   : UTC")
    print("Note       : Cached or sampled data are labelled; not a live simulation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
