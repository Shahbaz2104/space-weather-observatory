"""Solar Wind: the upstream conditions that can disturb the magnetosphere."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from spaceweather import ui
from spaceweather.processing.cleaning import valid_kp
from spaceweather.processing.resampling import infer_cadence_minutes
from spaceweather.visualization.timeseries import solar_wind_figure

mode, threshold = ui.sidebar_controls()
start, end = ui.date_range_controls(mode)

ui.render_page_header(
    "Upstream conditions",
    "Solar wind and the magnetosphere",
    "Speed, density, and the north–south IMF component near Earth, paired with the "
    "geomagnetic response. Recent windows use NOAA's propagated product; older "
    "windows use NASA OMNI2 hourly observations.",
)

try:
    with st.spinner("Loading solar-wind observations…"):
        bundle = ui.cached_solar_wind(mode, start.isoformat(), end.isoformat())
except Exception as exc:
    st.error(f"Unable to load solar wind: {exc}")
    ui.empty_state(
        "Switch to the offline sample (May 2024) or choose a window with available "
        "observations."
    )
    st.stop()

ui.render_status(bundle)
if bundle.frame.empty:
    ui.empty_state(
        "No solar-wind observations overlap this window. The offline sample covers "
        "May 2024; NOAA's propagated product covers approximately seven days."
    )
    st.stop()

wind = bundle.frame.copy()
wind["time_utc"] = pd.to_datetime(wind["time_utc"], utc=True, errors="coerce")
for column in ("speed_kms", "density_cm3", "bz_gsm_nt", "bt_nt", "temperature_k"):
    if column in wind:
        wind[column] = pd.to_numeric(wind[column], errors="coerce")

speed = wind["speed_kms"].dropna()
density = wind["density_cm3"].dropna()
bz = wind["bz_gsm_nt"].dropna()
negative_bz = float((bz < 0).mean() * 100.0) if not bz.empty else None
cadence = infer_cadence_minutes(wind)

ui.metric_cards(
    [
        {
            "label": "Median speed",
            "value": f"{speed.median():.0f} km/s" if not speed.empty else "—",
            "delta": f"max {speed.max():.0f}" if not speed.empty else None,
            "caption": f"{len(speed):,} valid samples",
            "help": "Arithmetic median of valid solar-wind speed values in the window.",
        },
        {
            "label": "Median density",
            "value": f"{density.median():.1f} p/cm³" if not density.empty else "—",
            "delta": f"max {density.max():.1f}" if not density.empty else None,
            "caption": f"{len(density):,} valid samples",
            "help": "Proton density; higher values can compress the magnetosphere.",
        },
        {
            "label": "Minimum Bz",
            "value": f"{bz.min():.1f} nT" if not bz.empty else "—",
            "delta": "southward" if not bz.empty and bz.min() < 0 else "northward",
            "caption": "GSM component",
            "help": (
                "Most negative Bz in the window. Southward (negative) Bz favors "
                "magnetic reconnection and energy transfer."
            ),
        },
        {
            "label": "Southward share",
            "value": f"{negative_bz:.0f}%" if negative_bz is not None else "—",
            "delta": "Bz < 0",
            "caption": "of valid Bz samples",
            "help": "Fraction of valid Bz observations below zero.",
        },
        {
            "label": "Median cadence",
            "value": f"{cadence:.0f} min" if cadence is not None else "—",
            "delta": "sample spacing",
            "caption": f"{len(wind):,} rows before validation",
            "help": (
                "Median interval between consecutive rows. NOAA's propagated "
                "product is one-minute; OMNI2 is hourly."
            ),
        },
    ]
)

st.markdown("")

try:
    kp_bundle = ui.load_window_cached(mode, start, end)
    kp_frame: pd.DataFrame | None = kp_bundle.frame
    kp_caption = kp_bundle.message
except Exception as exc:
    kp_frame = None
    kp_caption = f"Kp overlay unavailable: {exc}"

ui.show_plot(
    solar_wind_figure(
        wind,
        kp=kp_frame,
        threshold=threshold,
        height=760 if kp_frame is not None and not kp_frame.empty else 620,
    ),
    key="solar_wind_linked",
)
st.caption(
    f"{bundle.message} "
    + (
        f"Kp: {kp_caption} " if kp_frame is not None and not kp_frame.empty else ""
    )
    + "All panels share one UTC axis; no time shift is applied."
)

left, right = st.columns([1.4, 1], gap="large")
with left:
    st.subheader("Reading the panels")
    st.markdown(
        """
        - **Speed:** faster streams can increase the dynamic pressure on the
          magnetosphere and drive stronger convection.
        - **Bz (GSM):** southward fields (negative) permit magnetic reconnection
          at the dayside magnetopause, loading energy into the system.
        - **Kp:** a global, three-hour geomagnetic response index — not a local
          measurement and not a direct solar-wind quantity.
        - A visual alignment between a wind feature and a Kp rise is a hypothesis
          to test, not proof of a causal chain in this window.
        """
    )
    st.markdown(
        '<div class="swo-note">NOAA\'s geospace "propagated" solar wind is a '
        "modeled projection, not a direct in-situ measurement at Earth. OMNI2 "
        "values are hourly, time-shifted observations. Compare cadence and status "
        "before interpreting short-lived structure.</div>",
        unsafe_allow_html=True,
    )
with right:
    st.subheader("Coverage")
    valid_speed = int(wind["speed_kms"].notna().sum())
    valid_bz = int(wind["bz_gsm_nt"].notna().sum())
    cadence_text = f"{cadence:.0f} min" if cadence is not None else "—"
    st.markdown(
        f"- **Rows:** {len(wind):,}\n"
        f"- **Valid speed:** {valid_speed:,}\n"
        f"- **Valid Bz:** {valid_bz:,}\n"
        f"- **Median cadence:** {cadence_text}"
    )
    st.caption(
        "Missing values are gaps. They are not interpolated across panel joins or "
        "treated as zero."
    )
    if kp_frame is None or valid_kp(kp_frame).empty:
        st.caption("Kp overlay is unavailable; the wind panels stand alone.")

provenance = ui.provenance_for(
    bundle,
    threshold=threshold,
    transformations=[
        "Solar-wind fields coerced to numeric; invalid values preserved as missing.",
        "Kp overlay (when available) loaded for the same UTC window.",
    ],
)
left, right = st.columns(2)
with left:
    ui.download_frame(
        bundle.frame,
        filename="space-weather-solar-wind.csv",
        label="Download solar wind (CSV)",
        key="solar_wind_csv",
    )
with right:
    ui.download_provenance(
        provenance,
        filename="space-weather-solar-wind.provenance.json",
        key="solar_wind_provenance",
    )

with st.expander("Raw solar-wind rows"):
    preview = wind.sort_values("time_utc").tail(200).copy()
    preview["time_utc"] = preview["time_utc"].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(ui.display_frame(preview), hide_index=True, width="stretch")
    st.caption("Most recent 200 rows. The download contains the full selection.")
