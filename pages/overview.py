"""Overview: the state of the geospace environment at a glance."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from spaceweather import ui
from spaceweather.analysis.statistics import auto_summary, summary_metrics
from spaceweather.processing.cleaning import missing_summary
from spaceweather.processing.events import detect_events, events_to_frame
from spaceweather.visualization.distributions import kp_histogram_figure
from spaceweather.visualization.timeseries import kp_timeline_figure

mode, threshold = ui.sidebar_controls()
start, end = ui.date_range_controls(mode)

ui.render_page_header(
    "Geomagnetic conditions",
    "The Sun's magnetic footprint",
    "A measured view of planetary geomagnetic activity. Every value below is an "
    "observation with a stated source; nothing is forecast, interpolated, or filled.",
)

try:
    bundle = ui.load_window_cached(mode, start, end)
except Exception as exc:
    st.error(f"Unable to load Kp observations: {exc}")
    ui.empty_state(
        "The selected source could not be reached. Switch to the offline sample "
        "in the sidebar to explore the versioned observations."
    )
    st.stop()

ui.render_status(bundle)
if bundle.frame.empty:
    ui.empty_state(
        "No Kp observations exist for this window. Widen the time range or switch "
        "data mode."
    )
    st.stop()

metrics = summary_metrics(bundle.frame, threshold=threshold, start=start, end=end)
missing = missing_summary(bundle.frame, start=start, end=end)
events = detect_events(bundle.frame, threshold=threshold)

latest_caption = ui.format_ts(metrics["latest_time"])
peak_caption = ui.format_ts(metrics["peak_time"])
event_caption = (
    f"Longest sampled run · {metrics['longest_event_hours']:.0f} h"
    if metrics["event_count"]
    else "No run reaches the selected threshold"
)

ui.metric_cards(
    [
        {
            "label": "Latest Kp",
            "value": f"{metrics['latest_kp']:.2f}"
            if metrics["latest_kp"] is not None
            else "—",
            "delta": metrics["latest_status"],
            "caption": latest_caption,
            "help": (
                "Most recent valid three-hour Kp observation in the selection. "
                "NOAA values are preliminary; GFZ values may be definitive or preliminary."
            ),
        },
        {
            "label": "Peak Kp",
            "value": f"{metrics['peak_kp']:.2f}"
            if metrics["peak_kp"] is not None
            else "—",
            "delta": metrics["peak_g_scale"] or "below G1",
            "caption": peak_caption,
            "help": "Largest valid Kp value in the selection, with its NOAA G-scale band.",
        },
        {
            "label": "Storm samples",
            "value": f"{metrics['storm_samples']:,}",
            "delta": f"{metrics['storm_pct']:.1f}% of valid",
            "caption": f"Kp ≥ {threshold:g} in this window",
            "help": (
                "Count of three-hour observations at or above the storm threshold. "
                "This is not the number of physical storms."
            ),
        },
        {
            "label": "Data completeness",
            "value": f"{metrics['completeness']:.0%}",
            "delta": f"{missing['valid_rows']:,} valid slots",
            "caption": f"{missing['missing_rows']:,} missing / flagged",
            "help": (
                "Valid observations divided by expected three-hour slots in the "
                "window. Missing observations stay missing."
            ),
        },
        {
            "label": "Detected runs",
            "value": f"{metrics['event_count']:,}",
            "delta": metrics["peak_g_scale"] or "no G-scale",
            "caption": event_caption,
            "help": (
                "Contiguous runs of Kp at or above the threshold, allowing one "
                "missing three-hour slot between samples."
            ),
        },
    ]
)

st.markdown("")
ui.show_plot(
    kp_timeline_figure(
        bundle.frame,
        threshold=threshold,
        title="Planetary Kp · observed three-hour index",
        height=480,
    ),
    key="overview_timeline",
)
st.caption(
    "Kp timestamps mark the start of a three-hour interval. Shaded regions are "
    "contiguous threshold runs; missing slots break the line rather than being zero-filled."
)

left, right = st.columns([1.55, 1], gap="large")
with left:
    st.subheader("What the data says")
    for statement in auto_summary(
        bundle.frame, threshold=threshold, start=start, end=end
    ):
        st.markdown(f"- {statement}")
    st.markdown(
        '<div class="swo-note">Kp measures global geomagnetic disturbance. '
        "A statistical association with solar-wind conditions is not proof of "
        "causation, and none of these descriptive statistics is a forecast.</div>",
        unsafe_allow_html=True,
    )

with right:
    st.subheader("Most recent runs")
    if events:
        table = events_to_frame(events)
        table = table.sort_values("start_utc", ascending=False).head(5)
        display = pd.DataFrame(
            {
                "Start (UTC)": pd.to_datetime(table["start_utc"]).dt.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "Peak": table["peak_kp"].map(lambda value: f"{value:.2f}"),
                "G": table["g_scale"].fillna("—"),
                "Hours": table["duration_hours"].map(lambda value: f"{value:.0f}"),
                "Gap": table["missing_samples"].astype(int),
            }
        )
        st.dataframe(display, hide_index=True, width="stretch")
        st.caption(
            "Gap = missing three-hour slots inside a detected run. "
            "Duration spans sampled intervals, not the physical storm."
        )
    else:
        ui.empty_state(
            f"No contiguous run reaches Kp {threshold:g} in this selection. "
            "Lower the threshold in the sidebar to inspect weaker activity."
        )

st.divider()
left, right = st.columns(2, gap="large")
with left:
    st.subheader("Distribution")
    ui.show_plot(
        kp_histogram_figure(
            bundle.frame,
            threshold=threshold,
            title="How often each Kp level occurred",
        ),
        key="overview_histogram",
    )
with right:
    st.subheader("Data quality")
    st.markdown(
        f"- **Window:** {ui.format_ts(metrics['window_start'])} → "
        f"{ui.format_ts(metrics['window_end'])}\n"
        f"- **Valid observations:** {missing['valid_rows']:,}\n"
        f"- **Expected three-hour slots:** {missing['expected_slots']:,}\n"
        f"- **Missing / flagged rows:** {missing['missing_rows']:,}\n"
        f"- **Completeness:** {missing['completeness']:.1%}"
    )
    st.caption(
        "Completeness counts valid Kp values. A row can exist with a missing "
        "value; it remains visible in exports and is not converted to zero."
    )
    if bundle.warnings:
        for warning in bundle.warnings:
            st.caption(f"Note: {warning}")

st.divider()
st.subheader("Exports")
provenance = ui.provenance_for(
    bundle,
    threshold=threshold,
    transformations=[
        "Kp observations filtered to the selected UTC window.",
        "Storm runs detected from contiguous threshold exceedances.",
    ],
)
download_left, download_middle, download_right = st.columns(3)
with download_left:
    ui.download_frame(
        bundle.frame,
        filename="space-weather-kp-observations.csv",
        label="Download observations (CSV)",
        key="overview_observations_csv",
    )
with download_middle:
    ui.download_frame(
        events_to_frame(events),
        filename="space-weather-storm-runs.csv",
        label="Download detected runs (CSV)",
        key="overview_events_csv",
    )
with download_right:
    ui.download_provenance(
        provenance,
        filename="space-weather-provenance.json",
        key="overview_provenance_json",
    )
st.caption(
    "Exports preserve ISO-8601 UTC timestamps, all rows in the selection, and "
    "the source/missing-data policy in the provenance file."
)
