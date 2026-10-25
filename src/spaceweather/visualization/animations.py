"""Deterministic Matplotlib animation and static-figure exports."""

from __future__ import annotations

import math
import shutil
from datetime import UTC
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.animation as animation
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.artist import Artist

from spaceweather.exceptions import InsufficientDataError
from spaceweather.models import AnimationConfig
from spaceweather.processing.cleaning import valid_kp
from spaceweather.processing.events import detect_events, kp_to_g_scale
from spaceweather.visualization import theme

SUPPORTED_FORMATS = {"mp4", "gif"}


def encoder_available(fmt: str) -> bool:
    """Whether the requested encoder is available on this machine."""
    if fmt == "mp4":
        return shutil.which("ffmpeg") is not None
    return fmt == "gif"


def _prepare_observations(
    frame: pd.DataFrame, config: AnimationConfig
) -> tuple[pd.DataFrame, int, bool]:
    valid = valid_kp(frame)
    if len(valid) < 2:
        raise InsufficientDataError(
            "At least two valid observations are required to render an animation."
        )
    valid = valid.sort_values("time_utc").reset_index(drop=True)
    requested_stride = max(1, config.frame_stride)
    bounded_stride = max(1, math.ceil((len(valid) - 1) / (config.max_frames - 1)))
    stride = max(requested_stride, bounded_stride)
    sampled = valid.iloc[::stride].copy()
    if sampled.index[-1] != valid.index[-1]:
        sampled = pd.concat([sampled, valid.iloc[[-1]]], ignore_index=True)
    sampled = sampled.drop_duplicates("time_utc", keep="last").reset_index(drop=True)
    downsampled = stride > 1
    return sampled, stride, downsampled


def _header(
    figure: plt.Figure,
    *,
    title: str,
    subtitle: str,
    source_label: str,
) -> None:
    figure.text(
        0.075,
        0.925,
        title,
        color=theme.TEXT,
        fontsize=23,
        fontweight="bold",
        family="DejaVu Sans",
    )
    figure.text(
        0.076,
        0.885,
        subtitle,
        color=theme.CYAN,
        fontsize=9.5,
        fontweight="bold",
    )
    figure.text(
        0.97,
        0.885,
        source_label,
        color=theme.MUTED,
        fontsize=9,
        ha="right",
    )


def render_animation(
    frame: pd.DataFrame,
    output_path: str | Path,
    *,
    fmt: str = "mp4",
    config: AnimationConfig | None = None,
    title: str = "THE SUN'S MAGNETIC FOOTPRINT",
    subtitle: str = "SPACE WEATHER / OBSERVED DATA PLAYBACK",
    source_label: str = "OBSERVED · NOAA SWPC",
) -> dict[str, object]:
    """Render a chronological Kp playback as MP4 or GIF.

    The animation only visualizes real observations. No synthetic measurements
    or particle simulations are added. Frame sampling is reported in the result.
    """
    fmt = fmt.lower().lstrip(".")
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported animation format: {fmt}")
    if not encoder_available(fmt):
        raise RuntimeError(
            f"{fmt.upper()} export requires ffmpeg, which was not found on PATH. "
            "Use GIF or install ffmpeg."
        )

    config = config or AnimationConfig(threshold=5.0)
    observations, stride, downsampled = _prepare_observations(frame, config)
    times = pd.to_datetime(observations["time_utc"], utc=True)
    x = mdates.date2num(times.dt.to_pydatetime())
    values = observations["kp"].to_numpy(dtype=float)
    statuses = observations["status"].astype(str).tolist()
    threshold = float(config.threshold)

    with plt.rc_context(theme.matplotlib_style()):
        figure, (ax, ax2) = plt.subplots(
            2,
            1,
            figsize=(config.width, config.height),
            dpi=config.dpi,
            gridspec_kw={"height_ratios": [3.4, 1.0]},
        )
        figure.patch.set_facecolor(theme.BG)
        figure.subplots_adjust(
            left=0.075, right=0.97, top=0.80, bottom=0.135, hspace=0.18
        )
        for axis in (ax, ax2):
            axis.set_facecolor(theme.PANEL)
            axis.grid(axis="y", color=theme.GRID, alpha=0.45, linewidth=0.8)
            axis.spines[["top", "right", "left", "bottom"]].set_visible(False)
            axis.tick_params(colors=theme.MUTED, labelsize=9)

        _header(
            figure,
            title=title,
            subtitle=subtitle,
            source_label=source_label,
        )

        ax.set_ylim(0, 9.6)
        ax.set_xlim(x[0], x[-1] + 0.02)
        ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
        ax.set_ylabel("Kp INDEX (0–9)", fontsize=9, color=theme.MUTED)
        ax.axhline(
            threshold,
            color=theme.CORAL,
            linestyle="--",
            linewidth=1.2,
            alpha=0.9,
        )
        ax.text(
            x[0],
            threshold + 0.18,
            f"STORM THRESHOLD · Kp {threshold:g}",
            color=theme.CORAL,
            fontsize=8.5,
            fontweight="bold",
        )

        (glow,) = ax.plot(
            [], [], color=theme.CYAN, linewidth=7.0, alpha=0.10, solid_capstyle="round"
        )
        (line,) = ax.plot(
            [], [], color=theme.CYAN, linewidth=2.3, solid_capstyle="round"
        )
        (run_line,) = ax.plot(
            [], [], color=theme.VIOLET, linewidth=1.1, linestyle=":", alpha=0.95
        )
        (cursor,) = ax.plot([], [], color=theme.VIOLET, linewidth=1.0, alpha=0.8)
        (dot,) = ax.plot(
            [],
            [],
            marker="o",
            color=theme.CYAN,
            markersize=8,
            markeredgecolor="white",
            markeredgewidth=1.2,
            linestyle="none",
            zorder=6,
        )
        (run_dot,) = ax.plot(
            [],
            [],
            marker="*",
            color=theme.VIOLET,
            markersize=13,
            markeredgecolor=theme.TEXT,
            markeredgewidth=0.8,
            linestyle="none",
            zorder=6,
        )

        value_text = ax.text(
            0.012,
            0.955,
            "Kp —",
            transform=ax.transAxes,
            color=theme.TEXT,
            fontsize=25,
            fontweight="bold",
            family="DejaVu Sans Mono",
            va="top",
        )
        status_text = ax.text(
            0.013,
            0.845,
            "",
            transform=ax.transAxes,
            color=theme.MUTED,
            fontsize=8.5,
            va="top",
        )
        clock_text = ax.text(
            0.988,
            0.965,
            "",
            transform=ax.transAxes,
            color=theme.MUTED,
            fontsize=10,
            ha="right",
            va="top",
            family="DejaVu Sans Mono",
        )
        run_text = ax.text(
            0.988,
            0.905,
            "",
            transform=ax.transAxes,
            color=theme.VIOLET,
            fontsize=8.5,
            ha="right",
            va="top",
        )

        quiet_color = (0.32, 0.97, 0.89, 0.28)
        storm_color = (1.0, 0.36, 0.48, 0.85)
        bar_colors = [
            storm_color if value >= threshold else quiet_color for value in values
        ]
        ax2.bar(
            x,
            values,
            width=0.118,
            align="edge",
            color=bar_colors,
            edgecolor="none",
        )
        ax2.axhline(
            threshold, color=theme.CORAL, linestyle="--", linewidth=0.9, alpha=0.8
        )
        ax2.set_ylim(-0.2, 9.6)
        ax2.set_xlim(x[0], x[-1] + 0.02)
        ax2.set_yticks([])
        ax2.text(
            0.012,
            0.95,
            "3-HOUR SAMPLES",
            transform=ax2.transAxes,
            color=theme.MUTED,
            fontsize=7.5,
            ha="left",
            va="top",
            zorder=10,
        )
        ax2.text(
            0.99,
            0.95,
            "CORAL ≥ THRESHOLD",
            transform=ax2.transAxes,
            color=theme.MUTED,
            fontsize=7.5,
            ha="right",
            va="top",
            zorder=10,
        )
        mask = plt.Rectangle(
            (x[0], -0.2),
            0,
            10.0,
            facecolor=theme.PANEL,
            edgecolor="none",
            zorder=8,
            clip_on=True,
        )
        ax2.add_patch(mask)
        (bottom_cursor,) = ax2.plot(
            [], [], color=theme.VIOLET, linewidth=1.0, alpha=0.9, zorder=9
        )

        formatter = mdates.DateFormatter("%d %b\n%H:%M", tz=UTC)
        locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
        ax.xaxis.set_major_formatter(formatter)
        ax.xaxis.set_major_locator(locator)
        ax2.xaxis.set_major_formatter(formatter)
        ax2.xaxis.set_major_locator(locator)
        ax.tick_params(axis="x", colors=theme.MUTED, labelsize=8.5, labelbottom=False)
        ax2.tick_params(axis="x", colors=theme.MUTED, labelsize=8.5)

        peak_kp = float(np.max(values))
        storm_count = int(np.sum(values >= threshold))
        peak_g = kp_to_g_scale(peak_kp) or "below G1"
        footer = (
            f"PEAK Kp {peak_kp:.2f} ({peak_g})     "
            f"STORM-LEVEL SAMPLES {storm_count}     "
            f"THRESHOLD {threshold:g}     TIMEZONE UTC"
        )
        figure.text(0.075, 0.035, footer, color=theme.MUTED, fontsize=9)
        if downsampled:
            figure.text(
                0.97,
                0.035,
                f"FRAME SAMPLING · EVERY {stride}TH OBSERVATION",
                color=theme.MUTED,
                fontsize=8,
                ha="right",
            )

        def update(index: int) -> tuple[Artist, ...]:
            upto = index + 1
            x_slice = x[:upto]
            y_slice = values[:upto]
            glow.set_data(x_slice, y_slice)
            line.set_data(x_slice, y_slice)
            cursor.set_data([x[index], x[index]], [0, 9.6])
            dot.set_data([x[index]], [values[index]])
            running_max = float(np.max(y_slice))
            run_index = int(np.argmax(y_slice))
            run_line.set_data([x[0], x[index]], [running_max, running_max])
            run_dot.set_data([x[run_index]], [running_max])
            mask.set_x(x[index])
            mask.set_width(max(0.0, x[-1] - x[index] + 0.12))
            bottom_cursor.set_data([x[index], x[index]], [-0.2, 9.6])
            value_text.set_text(f"Kp {values[index]:.2f}")
            value_text.set_color(
                theme.CORAL if values[index] >= threshold else theme.TEXT
            )
            status_text.set_text(
                f"{statuses[index].upper()} OBSERVATION · 3-HOUR INTERVAL"
            )
            clock_text.set_text(times.iloc[index].strftime("%d %b %Y · %H:%M UTC"))
            run_text.set_text(f"RUNNING MAX  {running_max:.2f}")
            return (
                glow,
                line,
                run_line,
                cursor,
                dot,
                run_dot,
                mask,
                bottom_cursor,
                value_text,
                status_text,
                clock_text,
                run_text,
            )

        frames = len(observations)
        anim = animation.FuncAnimation(
            figure,
            update,
            frames=frames,
            interval=1000.0 / config.fps,
            blit=False,
            repeat=False,
        )

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        writer: animation.AbstractMovieWriter
        if fmt == "mp4":
            writer = animation.FFMpegWriter(
                fps=config.fps,
                codec="libx264",
                bitrate=2400,
                extra_args=["-pix_fmt", "yuv420p"],
            )
        else:
            writer = animation.PillowWriter(fps=config.fps)
        anim.save(output, writer=writer, dpi=config.dpi)
        plt.close(figure)

    return {
        "path": str(output),
        "format": fmt,
        "frames": frames,
        "fps": config.fps,
        "duration_seconds": frames / config.fps,
        "frame_stride": stride,
        "downsampled": downsampled,
        "observations": len(observations),
        "threshold": threshold,
        "seed": config.seed,
        "width": config.width,
        "height": config.height,
        "dpi": config.dpi,
        "first_time_utc": times.iloc[0].isoformat(),
        "last_time_utc": times.iloc[-1].isoformat(),
    }


def save_kp_overview_png(
    frame: pd.DataFrame,
    output_path: str | Path,
    *,
    threshold: float = 5.0,
    title: str = "THE SUN'S MAGNETIC FOOTPRINT",
    subtitle: str = "SPACE WEATHER / OBSERVED Kp OVERVIEW",
    source_label: str = "OBSERVED · NOAA SWPC",
    width: float = 14.0,
    height: float = 7.5,
    dpi: int = 200,
) -> str:
    """Save a high-resolution static overview figure."""
    valid = valid_kp(frame).sort_values("time_utc")
    if valid.empty:
        raise InsufficientDataError("No valid observations to plot")
    times = pd.to_datetime(valid["time_utc"], utc=True)
    x = mdates.date2num(times.dt.to_pydatetime())
    values = valid["kp"].to_numpy(dtype=float)

    with plt.rc_context(theme.matplotlib_style()):
        figure, ax = plt.subplots(figsize=(width, height), dpi=dpi)
        figure.patch.set_facecolor(theme.BG)
        figure.subplots_adjust(left=0.075, right=0.965, top=0.80, bottom=0.16)
        ax.set_facecolor(theme.PANEL)
        ax.grid(axis="y", color=theme.GRID, alpha=0.45, linewidth=0.8)
        ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
        ax.tick_params(colors=theme.MUTED, labelsize=9)

        _header(figure, title=title, subtitle=subtitle, source_label=source_label)

        for event in detect_events(valid, threshold=threshold):
            ax.axvspan(
                mdates.date2num(event.start_utc),
                mdates.date2num(event.end_utc),
                color=theme.CORAL,
                alpha=0.07,
                linewidth=0,
            )
        ax.fill_between(x, 0, values, color=theme.CYAN, alpha=0.08)
        ax.plot(x, values, color=theme.CYAN, linewidth=2.3)
        ax.scatter(x, values, color=theme.CYAN, s=12, zorder=3)
        ax.axhline(
            threshold,
            color=theme.CORAL,
            linestyle="--",
            linewidth=1.2,
            alpha=0.9,
        )
        ax.text(
            x[0],
            threshold + 0.2,
            f"STORM THRESHOLD · Kp {threshold:g}",
            color=theme.CORAL,
            fontsize=9,
            fontweight="bold",
        )

        peak_index = int(np.argmax(values))
        ax.scatter(
            [x[peak_index]],
            [values[peak_index]],
            color=theme.VIOLET,
            s=90,
            marker="D",
            edgecolor=theme.TEXT,
            linewidth=1.0,
            zorder=5,
        )
        ax.annotate(
            f"PEAK Kp {values[peak_index]:.2f}",
            xy=(x[peak_index], values[peak_index]),
            xytext=(10, 16),
            textcoords="offset points",
            color=theme.VIOLET,
            fontsize=9,
            fontweight="bold",
        )

        ax.set_ylim(0, 9.6)
        ax.set_xlim(x[0], x[-1])
        ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
        ax.set_ylabel("Kp INDEX (0–9)", fontsize=9, color=theme.MUTED)
        formatter = mdates.DateFormatter("%d %b\n%H:%M", tz=UTC)
        ax.xaxis.set_major_formatter(formatter)
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=8))
        figure.text(0.075, 0.045, "TIMEZONE UTC", color=theme.MUTED, fontsize=9)
        figure.text(
            0.965,
            0.045,
            f"{len(valid)} VALID OBSERVATIONS · Kp ≥ {threshold:g}: "
            f"{int((values >= threshold).sum())}",
            color=theme.MUTED,
            fontsize=9,
            ha="right",
        )

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(
            output,
            dpi=dpi,
            facecolor=theme.BG,
            bbox_inches="tight",
            pad_inches=0.35,
        )
        plt.close(figure)
    return str(output)
