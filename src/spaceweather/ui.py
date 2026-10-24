"""Streamlit presentation helpers shared by every page."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from spaceweather import __version__
from spaceweather.config import get_settings
from spaceweather.export.reports import build_provenance, provenance_json_bytes
from spaceweather.ingestion.samples import sample_kp_years
from spaceweather.models import AnimationConfig, DataBundle, DataStatus, Provenance
from spaceweather.services import (
    load_correlation_data,
    load_kp_historical,
    load_kp_window,
    load_solar_wind_window,
)
from spaceweather.visualization.theme import (
    BG,
    BORDER,
    CORAL,
    CYAN,
    MUTED,
    TEXT,
    register_plotly_template,
)

register_plotly_template()

MODE_LABELS = {
    "Auto — live with sample fallback": "auto",
    "Live only — fail visibly": "live",
    "Offline sample — versioned observations": "offline",
}

CSS = f"""
<style>
:root {{
  --swo-bg: {BG};
  --swo-panel: #10182A;
  --swo-border: {BORDER};
  --swo-cyan: {CYAN};
  --swo-violet: #9B87FF;
  --swo-coral: {CORAL};
  --swo-text: {TEXT};
  --swo-muted: {MUTED};
}}
.stApp {{
  background:
    radial-gradient(1100px 520px at 12% -12%, rgba(82,246,227,0.055), transparent 60%),
    radial-gradient(900px 480px at 100% 0%, rgba(155,135,255,0.06), transparent 58%),
    var(--swo-bg);
}}
.block-container {{ padding-top: 4.6rem; padding-bottom: 3rem; max-width: 1500px; }}
h1, h2, h3, h4 {{ font-family: "Inter","Segoe UI",system-ui,sans-serif; letter-spacing: -0.025em; }}
p, li {{ color: #A9B6CE; }}
a {{ color: var(--swo-cyan); }}
[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, #0A1120 0%, #070C17 100%);
  border-right: 1px solid #1B2740;
}}
[data-testid="stSidebar"] .block-container {{ padding-top: 1.1rem; }}
[data-testid="stSidebar"] hr {{ border-color: #1B2740; }}
.swo-brand {{ display:flex; align-items:center; gap:.7rem; padding:.35rem 0 1.1rem; }}
.swo-brand__dot {{
  width:9px; height:9px; border-radius:50%; background:var(--swo-cyan);
  box-shadow:0 0 14px rgba(82,246,227,.9); flex:none;
}}
.swo-brand__text {{ font-size:.72rem; letter-spacing:.18em; color:var(--swo-muted); line-height:1.35; text-transform:uppercase; }}
.swo-brand__text b {{ color:var(--swo-text); font-size:.86rem; letter-spacing:.12em; }}
.swo-kicker {{
  color:var(--swo-cyan); font-size:.7rem; letter-spacing:.2em; text-transform:uppercase;
  font-weight:650; margin-bottom:.4rem;
}}
.swo-title {{
  font-size:clamp(1.9rem, 3.2vw, 3rem); line-height:1.02; margin:0 0 .55rem;
  font-weight:700; color:var(--swo-text);
}}
.swo-lede {{ color:var(--swo-muted); max-width:76ch; font-size:.98rem; line-height:1.6; margin:0 0 1.25rem; }}
.swo-statusline {{ display:flex; flex-wrap:wrap; gap:.45rem; align-items:center; margin:.1rem 0 1.1rem; }}
.swo-badge {{
  display:inline-flex; align-items:center; gap:.35rem; border:1px solid var(--swo-border);
  border-radius:999px; padding:.2rem .55rem; font-size:.68rem; letter-spacing:.08em;
  text-transform:uppercase; color:var(--swo-muted); background:rgba(16,24,42,.55);
}}
.swo-badge--live {{ color:#6BE3A3; border-color:rgba(107,227,163,.32); background:rgba(107,227,163,.07); }}
.swo-badge--sample {{ color:#FFC46B; border-color:rgba(255,196,107,.34); background:rgba(255,196,107,.08); }}
.swo-badge--stale {{ color:var(--swo-coral); border-color:rgba(255,92,122,.34); background:rgba(255,92,122,.08); }}
.swo-badge--estimated {{ color:#FFC46B; border-color:rgba(255,196,107,.34); background:rgba(255,196,107,.08); }}
.swo-badge--preliminary {{ color:#B9C4D8; border-color:rgba(185,196,216,.28); background:rgba(185,196,216,.06); }}
.swo-badge--accent {{ color:var(--swo-cyan); border-color:rgba(82,246,227,.32); background:rgba(82,246,227,.06); }}
[data-testid="stMetric"] {{
  background: linear-gradient(180deg, rgba(16,24,42,.97), rgba(12,20,36,.97));
  border:1px solid var(--swo-border); border-radius:14px; padding:.95rem 1.05rem;
  box-shadow: 0 14px 34px rgba(0,0,0,.18);
}}
[data-testid="stMetricLabel"] p {{
  color:var(--swo-muted); font-size:.68rem; text-transform:uppercase; letter-spacing:.13em;
}}
[data-testid="stMetricValue"] {{
  color:var(--swo-text); font-family:"DejaVu Sans Mono",monospace; font-variant-numeric:tabular-nums;
  font-size:1.6rem; line-height:1.18;
}}
[data-testid="stMetricDelta"] {{ font-size:.72rem; }}
.stButton > button, .stDownloadButton > button {{
  background:#0D1626; color:var(--swo-cyan); border:1px solid rgba(82,246,227,.32);
  border-radius:10px; font-weight:600; letter-spacing:.01em;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
  border-color:var(--swo-cyan); color:#CFFFF8; box-shadow:0 0 0 1px rgba(82,246,227,.18);
}}
[data-testid="stDataFrame"] {{ border:1px solid var(--swo-border); border-radius:12px; overflow:hidden; }}
[data-testid="stAlert"] {{ border-radius:11px; }}
.swo-empty {{
  border:1px dashed #2A3A58; border-radius:14px; padding:1.35rem 1.4rem;
  color:var(--swo-muted); background:rgba(16,24,42,.5); font-size:.9rem;
}}
.swo-note {{
  border-left:2px solid var(--swo-cyan); padding:.65rem .95rem;
  background:rgba(82,246,227,.035); color:#A9B6CE; font-size:.84rem; line-height:1.55;
}}
.swo-footer {{ color:#5E6C84; font-size:.72rem; line-height:1.6; padding-top:.4rem; }}
.swo-mono {{ font-family:"DejaVu Sans Mono",monospace; font-variant-numeric:tabular-nums; }}
details summary {{ color:var(--swo-muted) !important; }}
[data-testid="stExpander"] {{ border:1px solid var(--swo-border); border-radius:12px; background:rgba(16,24,42,.35); }}
</style>
"""


def inject_css() -> None:
    """Apply the observatory stylesheet."""
    st.markdown(CSS, unsafe_allow_html=True)


def render_brand() -> None:
    """Render the sidebar brand block."""
    st.sidebar.markdown(
        """
        <div class="swo-brand">
          <span class="swo-brand__dot"></span>
          <span class="swo-brand__text">Space Weather<br><b>Observatory</b></span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_controls() -> tuple[str, float]:
    """Render mode and threshold controls; return the resolved mode and threshold.

    The controls are driven by plain session-state values rather than widget keys.
    Streamlit discards widget-key state when the selected page changes, which would
    silently reset the data mode on navigation and could show live data to someone
    who had deliberately chosen the offline sample.
    """
    st.sidebar.markdown(
        '<div class="swo-kicker">Data mode</div>', unsafe_allow_html=True
    )
    labels = list(MODE_LABELS)
    current_label = st.session_state.get("swo_mode_value")
    mode_index = labels.index(current_label) if current_label in labels else 0
    label = st.sidebar.radio(
        "Source behaviour",
        labels,
        index=mode_index,
        label_visibility="collapsed",
        help=(
            "Auto uses live sources and falls back to the bundled genuine-data "
            "sample with a visible warning. Live-only fails visibly. Offline uses "
            "only the versioned sample."
        ),
    )
    st.session_state["swo_mode_value"] = label
    mode = MODE_LABELS[str(label)]
    st.sidebar.markdown(
        '<div class="swo-kicker" style="margin-top:1.1rem">Storm threshold</div>',
        unsafe_allow_html=True,
    )
    threshold = st.sidebar.slider(
        "Kp threshold",
        min_value=3.0,
        max_value=9.0,
        value=float(st.session_state.get("swo_threshold_value", 5.0)),
        step=0.1,
        label_visibility="collapsed",
        help=(
            "The conventional NOAA G1 threshold is Kp 5.0. Changing this threshold "
            "changes event detection; G-scale labels still use the official 5-9 bands."
        ),
    )
    # Sliders report binary float drift (6.800000190734863); keep a one-decimal value.
    st.session_state["swo_threshold_value"] = round(float(threshold), 1)
    st.sidebar.caption("NOAA G1 begins at Kp 5.0. G-scale labels are independent of this slider.")
    st.sidebar.divider()
    st.sidebar.caption(f"v{__version__} · UTC · NOAA / GFZ / NASA")
    return mode, float(threshold)


def default_dates_for_mode(mode: str) -> tuple[date, date]:
    """Default date range for a data mode."""
    if mode == "offline":
        return date(2024, 5, 1), date(2024, 5, 31)
    today = date.today()
    return today - timedelta(days=6), today


def available_dates_for_mode(mode: str) -> tuple[date, date]:
    """Available date bounds for the date picker."""
    if mode == "offline":
        settings = get_settings()
        years = sample_kp_years(settings)
        if years:
            return date(min(years), 1, 1), date(max(years), 12, 31)
        return date(2024, 1, 1), date(2024, 12, 31)
    return date(1932, 1, 1), date.today()


def date_range_controls(mode: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Render the shared UTC date range control and return inclusive timestamps."""
    bounds = available_dates_for_mode(mode)
    default_start, default_end = default_dates_for_mode(mode)
    state_key = "swo_date_range_value"
    mode_key = "swo_date_mode"
    if st.session_state.get(mode_key) != mode:
        st.session_state[mode_key] = mode
        st.session_state[state_key] = (default_start, default_end)
    stored_range = st.session_state.get(state_key)
    if not (isinstance(stored_range, (tuple, list)) and len(stored_range) == 2):
        stored_range = (default_start, default_end)
        st.session_state[state_key] = stored_range
    st.sidebar.markdown(
        '<div class="swo-kicker">Time window (UTC)</div>', unsafe_allow_html=True
    )
    picked = st.sidebar.date_input(
        "Time window",
        value=stored_range,
        min_value=bounds[0],
        max_value=bounds[1],
        label_visibility="collapsed",
        help="All timestamps are UTC. The end date is inclusive.",
    )
    st.session_state[state_key] = picked
    if isinstance(picked, (tuple, list)) and len(picked) == 2:
        start_date, end_date = picked
    elif isinstance(picked, date):
        start_date = end_date = picked
    else:
        start_date, end_date = default_start, default_end
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    start = pd.Timestamp(datetime.combine(start_date, time.min, tzinfo=UTC))
    end = pd.Timestamp(
        datetime.combine(end_date, time(23, 59, 59), tzinfo=UTC)
    )
    return start, end


def render_page_header(kicker: str, title: str, description: str) -> None:
    """Render the consistent page heading."""
    st.markdown(
        f"""
        <div class="swo-kicker">{kicker}</div>
        <h1 class="swo-title">{title}</h1>
        <p class="swo-lede">{description}</p>
        """,
        unsafe_allow_html=True,
    )


def format_ts(value: datetime | pd.Timestamp | None) -> str:
    """Format a UTC timestamp for display."""
    if value is None:
        return "—"
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    return timestamp.strftime("%Y-%m-%d %H:%M UTC")


def _latest_retrieval(bundle: DataBundle) -> datetime | None:
    values = [
        source.retrieved_at
        for source in bundle.sources
        if source.retrieved_at is not None
    ]
    return max(values) if values else bundle.last_updated


def render_status(bundle: DataBundle) -> None:
    """Show source, mode, and staleness badges."""
    badges: list[str] = []
    if bundle.is_sample:
        badges.append(
            '<span class="swo-badge swo-badge--sample">Offline sample · not live</span>'
        )
    else:
        badges.append('<span class="swo-badge swo-badge--live">Live source</span>')
    statuses = {source.status for source in bundle.sources}
    if DataStatus.ESTIMATED in statuses or DataStatus.FORECAST in statuses:
        badges.append(
            '<span class="swo-badge swo-badge--estimated">'
            "Modeled / propagated · not direct observation</span>"
        )
    if DataStatus.PRELIMINARY in statuses:
        badges.append(
            '<span class="swo-badge swo-badge--preliminary">'
            "Preliminary · may be revised</span>"
        )
    # The sample loaders flag themselves as cached/stale so they can never be read
    # as live. That is already said by the offline badge and warning, so the HTTP
    # cache badges are only meaningful for real fetches.
    if not bundle.is_sample:
        if any(source.from_cache for source in bundle.sources):
            badges.append('<span class="swo-badge">Cache used</span>')
        if any(source.stale for source in bundle.sources):
            badges.append(
                '<span class="swo-badge swo-badge--stale">'
                "Stale cache · source unavailable</span>"
            )
    badges.append('<span class="swo-badge swo-badge--accent">Timezone · UTC</span>')
    names = ", ".join(sorted({source.name for source in bundle.sources})) or "Unavailable"
    retrieved = _latest_retrieval(bundle)
    badges.append(
        f'<span class="swo-badge">Last source update · {format_ts(retrieved)}</span>'
    )
    st.markdown(
        f'<div class="swo-statusline">{"".join(badges)}</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Source: {names}. {bundle.message}")
    if bundle.is_sample:
        st.warning(
            "This view uses the versioned offline sample of genuine observations. "
            "It is not a live feed and must not be read as current space weather."
        )
    for warning in bundle.warnings:
        if bundle.is_sample and warning.startswith("This is a versioned sample"):
            continue
        st.warning(warning)


def metric_cards(items: Iterable[dict[str, object]]) -> None:
    """Render a row of metric cards with optional help text and captions."""
    entries = list(items)
    columns = st.columns(len(entries))
    for column, item in zip(columns, entries, strict=True):
        with column:
            st.metric(
                str(item.get("label", "")),
                str(item.get("value", "—")),
                delta=str(item["delta"]) if item.get("delta") is not None else None,
                delta_color="off",
                help=str(item["help"]) if item.get("help") else None,
            )
            if item.get("caption"):
                st.caption(str(item["caption"]))


def display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Copy a frame for display without non-serializable internal attributes."""
    output = frame.copy()
    output.attrs = {}
    return output


def show_plot(figure: go.Figure, *, key: str | None = None) -> None:
    """Render a Plotly figure with sensible interaction settings."""
    st.plotly_chart(
        figure,
        width="stretch",
        config={
            "displaylogo": False,
            "scrollZoom": True,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        },
        key=key,
    )


def empty_state(message: str) -> None:
    """Render a consistent empty state."""
    st.markdown(f'<div class="swo-empty">{message}</div>', unsafe_allow_html=True)


def download_frame(
    frame: pd.DataFrame,
    *,
    filename: str,
    label: str = "Download CSV",
    key: str,
) -> None:
    """Download a dataframe as UTF-8 CSV."""
    from spaceweather.export.reports import frame_to_csv_bytes

    st.download_button(
        label,
        data=frame_to_csv_bytes(frame),
        file_name=filename,
        mime="text/csv",
        key=key,
    )


def download_provenance(provenance: Provenance, *, filename: str, key: str) -> None:
    """Download provenance JSON."""
    st.download_button(
        "Download provenance JSON",
        data=provenance_json_bytes(provenance),
        file_name=filename,
        mime="application/json",
        key=key,
    )


def provenance_for(
    bundle: DataBundle,
    *,
    threshold: float,
    transformations: list[str] | None = None,
    animation: AnimationConfig | None = None,
    extra_notes: dict[str, object] | None = None,
) -> Provenance:
    """Build provenance using project defaults."""
    return build_provenance(
        bundle,
        threshold=threshold,
        transformations=transformations,
        animation=animation,
        extra_notes=extra_notes,
    )


def sidebar_footer() -> None:
    """Render attribution at the bottom of the sidebar."""
    st.sidebar.divider()
    st.sidebar.markdown(
        """
        <div class="swo-footer">
        NOAA SWPC · GFZ Kp (CC BY 4.0) · NASA OMNI.<br>
        Research and education only. Not an operational forecast.
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=600, show_spinner=False)
def cached_kp_window(mode: str, start_iso: str, end_iso: str) -> DataBundle:
    """Cached Kp window loader."""
    return load_kp_window(
        mode,
        start=pd.Timestamp(start_iso).to_pydatetime(),
        end=pd.Timestamp(end_iso).to_pydatetime(),
    )


@st.cache_data(ttl=3600, show_spinner=False)
def cached_kp_historical(mode: str) -> DataBundle:
    """Cached full-history Kp loader."""
    return load_kp_historical(mode)


@st.cache_data(ttl=600, show_spinner=False)
def cached_solar_wind(mode: str, start_iso: str, end_iso: str) -> DataBundle:
    """Cached solar-wind window loader."""
    return load_solar_wind_window(
        mode,
        start=pd.Timestamp(start_iso).to_pydatetime(),
        end=pd.Timestamp(end_iso).to_pydatetime(),
    )


@st.cache_data(ttl=600, show_spinner=False)
def cached_pair(
    mode: str, start_iso: str, end_iso: str
) -> tuple[DataBundle, DataBundle, pd.DataFrame]:
    """Cached aligned Kp/solar-wind loader."""
    return load_correlation_data(
        mode,
        start=pd.Timestamp(start_iso).to_pydatetime(),
        end=pd.Timestamp(end_iso).to_pydatetime(),
    )


def load_window_cached(
    mode: str, start: pd.Timestamp, end: pd.Timestamp
) -> DataBundle:
    """Load a Kp window using ISO strings as cache keys."""
    return cached_kp_window(mode, start.isoformat(), end.isoformat())


def source_attribution_markdown() -> str:
    """Return attribution text suitable for Markdown pages."""
    return (
        "**NOAA SWPC** — U.S. Government work, public domain. "
        "**GFZ Helmholtz Centre for Geosciences** — Kp data under CC BY 4.0; "
        "cite Matzka et al. (2021), https://doi.org/10.1029/2020SW002641. "
        "**NASA OMNIWeb** — OMNI2 hourly data, NASA usage guidance."
    )
