"""Animation Studio: a deterministic playback of observed Kp."""

from __future__ import annotations

import hashlib
from pathlib import Path

import streamlit as st

from spaceweather import ui
from spaceweather.config import get_settings
from spaceweather.models import AnimationConfig
from spaceweather.visualization.animations import encoder_available, render_animation

mode, threshold = ui.sidebar_controls()
start, end = ui.date_range_controls(mode)

ui.render_page_header(
    "Observed playback",
    "Animation Studio",
    "Render the selected Kp observations as a chronological film. Frames are "
    "sampled from real measurements only — no synthetic particles, no interpolated "
    "science, no forecast.",
)

try:
    bundle = ui.load_window_cached(mode, start, end)
except Exception as exc:
    st.error(f"Unable to load Kp observations: {exc}")
    st.stop()

ui.render_status(bundle)
if bundle.frame.empty:
    ui.empty_state("No Kp observations exist for this window.")
    st.stop()

settings = get_settings()
settings.ensure_directories()
source_names = ", ".join(sorted({source.name for source in bundle.sources})) or "observed"
if bundle.is_sample:
    source_label = "OFFLINE SAMPLE · GFZ Kp"
    subtitle = "SPACE WEATHER / VERSIONED SAMPLE PLAYBACK"
else:
    source_label = f"OBSERVED · {source_names.upper()}"
    subtitle = "SPACE WEATHER / OBSERVED DATA PLAYBACK"

left, middle, right = st.columns([1, 1, 1])
with left:
    fmt = st.selectbox(
        "Format",
        ["gif", "mp4"],
        index=0,
        key="animation_format",
        help="GIF works everywhere; MP4 is smaller and smoother for longer windows.",
        format_func=lambda value: value.upper(),
    )
with middle:
    fps = st.slider(
        "Frames per second",
        min_value=4,
        max_value=30,
        value=10,
        step=1,
        key="animation_fps",
    )
with right:
    stride = st.slider(
        "Frame stride",
        min_value=1,
        max_value=10,
        value=1,
        step=1,
        key="animation_stride",
        help="Use every Nth observation. A hard cap of 600 frames is also applied.",
    )

left, middle, right = st.columns([1, 1, 1])
with left:
    width = st.slider(
        "Figure width (inches)",
        min_value=9.0,
        max_value=16.0,
        value=12.0,
        step=0.5,
        key="animation_width",
    )
with middle:
    height = st.slider(
        "Figure height (inches)",
        min_value=5.0,
        max_value=10.0,
        value=6.4,
        step=0.2,
        key="animation_height",
    )
with right:
    dpi = st.select_slider(
        "Resolution (DPI)",
        options=[80, 100, 120, 150],
        value=100,
        key="animation_dpi",
    )

if fmt == "mp4" and not encoder_available("mp4"):
    st.warning(
        "MP4 export requires ffmpeg on PATH. Choose GIF or install ffmpeg."
    )
    fmt = "gif"

config = AnimationConfig(
    fps=int(fps),
    frame_stride=int(stride),
    width=float(width),
    height=float(height),
    dpi=int(dpi),
    max_frames=600,
    seed=42,
    threshold=float(threshold),
)
signature = hashlib.sha1(
    (
        f"{mode}|{start.isoformat()}|{end.isoformat()}|{config.model_dump_json()}|"
        f"{fmt}"
    ).encode()
).hexdigest()[:12]

st.markdown(
    '<div class="swo-note">Rendering is deterministic for identical settings. '
    "The frame cap and any stride are reported in the metadata and provenance. "
    "Animations replay observations; they do not simulate physics or predict the "
    "future.</div>",
    unsafe_allow_html=True,
)

render_clicked = st.button(
    "Render animation",
    type="primary",
    key="animation_render_button",
    disabled=fmt == "mp4" and not encoder_available("mp4"),
)

if render_clicked:
    output_path = settings.output_dir / f"swo-animation-{signature}.{fmt}"
    try:
        with st.spinner("Rendering frames… this can take a few moments."):
            result = render_animation(
                bundle.frame,
                output_path,
                fmt=fmt,
                config=config,
                title="THE SUN'S MAGNETIC FOOTPRINT",
                subtitle=subtitle,
                source_label=source_label,
            )
    except Exception as exc:
        st.error(f"Animation could not be rendered: {exc}")
    else:
        result["signature"] = signature
        result["source_label"] = source_label
        st.session_state["swo_animation"] = result
        st.session_state["swo_animation_bundle"] = bundle
        st.success(f"Rendered {result['frames']} frames at {result['fps']} fps.")

stored = st.session_state.get("swo_animation")
if stored and stored.get("signature") == signature:
    path = Path(str(stored["path"]))
    if path.exists():
        st.subheader("Preview")
        if stored["format"] == "gif":
            st.image(str(path))
        else:
            st.video(path.read_bytes())
        size_mb = path.stat().st_size / (1024 * 1024)
        st.caption(
            f"{stored['frames']} frames · {stored['fps']} fps · "
            f"{stored['duration_seconds']:.1f} s · stride {stored['frame_stride']} · "
            f"{size_mb:.1f} MB · {stored['width']:.1f}×{stored['height']:.1f} in "
            f"at {stored['dpi']} DPI"
        )
        mime = "image/gif" if stored["format"] == "gif" else "video/mp4"
        st.download_button(
            f"Download {stored['format'].upper()}",
            data=path.read_bytes(),
            file_name=f"space-weather-playback.{stored['format']}",
            mime=mime,
            key="animation_download",
        )

        bundle_for_provenance = st.session_state.get("swo_animation_bundle", bundle)
        provenance = ui.provenance_for(
            bundle_for_provenance,
            threshold=threshold,
            transformations=[
                f"Rendered {stored['frames']} frames from valid Kp observations.",
                f"Applied frame stride {stored['frame_stride']}; "
                f"downsampled={stored['downsampled']}.",
                "No synthetic or interpolated values were added.",
            ],
            animation=config,
            extra_notes={
                "animation_file": str(path.name),
                "frame_stride": stored["frame_stride"],
                "frames": stored["frames"],
                "fps": stored["fps"],
                "duration_seconds": stored["duration_seconds"],
                "first_time_utc": stored["first_time_utc"],
                "last_time_utc": stored["last_time_utc"],
            },
        )
        ui.download_provenance(
            provenance,
            filename="space-weather-animation.provenance.json",
            key="animation_provenance",
        )
else:
    st.caption(
        "Choose a focused window in the sidebar, set the playback rate, and render. "
        "Long windows are capped at 600 frames."
    )

st.divider()
st.subheader("What appears in every frame")
st.markdown(
    """
    - **Kp value and G-scale:** the current observed three-hour sample.
    - **Cyan trace:** all observations up to the current frame.
    - **Violet running maximum:** the highest Kp seen so far in the sequence.
    - **Bottom panel:** every sampled observation; coral bars meet the threshold.
    - **Clock and status:** UTC interval start and whether the source is
      preliminary or definitive.

    Event duration in the animation is the sampled span, not the physical lifetime
    of a geomagnetic disturbance. The running maximum is a display aid, not a
    detected event boundary.
    """
)
