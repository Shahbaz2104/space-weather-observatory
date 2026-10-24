"""Storm Explorer: inspect one detected threshold run in context."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from spaceweather import ui
from spaceweather.analysis.statistics import summary_metrics
from spaceweather.processing.events import detect_events, events_to_frame
from spaceweather.visualization.timeseries import (
    event_window_figure,
    kp_timeline_figure,
    solar_wind_figure,
)

mode, threshold = ui.sidebar_controls()
start, end = ui.date_range_controls(mode)

ui.render_page_header(
    "Event forensics",
    "Storm Explorer",
    "Isolate one contiguous threshold run, inspect its samples, and compare it with "
    "the solar wind that arrived around it. Detection is transparent arithmetic, "
    "not an official storm catalog.",
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

events = detect_events(bundle.frame, threshold=threshold)
if not events:
    metrics = summary_metrics(
        bundle.frame, threshold=threshold, start=start, end=end
    )
    ui.empty_state(
        f"No contiguous run reaches Kp {threshold:g} between {ui.format_ts(start)} "
        f"and {ui.format_ts(end)}. The activity in this window is shown below so you "
        "can judge how far it stayed below the threshold."
    )
    ui.metric_cards(
        [
            {
                "label": "Peak Kp",
                "value": f"{metrics['peak_kp']:.2f}"
                if metrics["peak_kp"] is not None
                else "—",
                "delta": metrics["peak_g_scale"] or "below G1",
                "caption": ui.format_ts(metrics["peak_time"]),
                "help": "Largest valid Kp sample in the selected window.",
            },
            {
                "label": "Latest Kp",
                "value": f"{metrics['latest_kp']:.2f}"
                if metrics["latest_kp"] is not None
                else "—",
                "delta": metrics["latest_status"],
                "caption": ui.format_ts(metrics["latest_time"]),
                "help": "Most recent valid Kp sample in the selected window.",
            },
            {
                "label": "Storm samples",
                "value": f"{metrics['storm_samples']:,}",
                "delta": f"threshold Kp {threshold:g}",
                "caption": f"{metrics['completeness']:.0%} window completeness",
                "help": "Count of samples at or above the selected threshold.",
            },
        ]
    )
    ui.show_plot(
        kp_timeline_figure(
            bundle.frame,
            threshold=threshold,
            title="Planetary Kp · selection context",
            height=430,
        ),
        key="storm_empty_timeline",
    )
    st.caption(
        "A threshold run is arithmetic: a quiet window can still contain a short "
        "excursion. Lower the threshold in the sidebar to inspect weaker activity."
    )
    st.stop()

context = (threshold, start.isoformat(), end.isoformat(), mode)
if st.session_state.get("swo_event_context") != context:
    st.session_state["swo_event_context"] = context
    st.session_state["swo_event_index"] = 0

labels = []
for event in events:
    g_scale = event.g_scale or "below G1"
    labels.append(
        f"{ui.format_ts(event.start_utc)} · Kp {event.peak_kp:.2f} ({g_scale}) · "
        f"{event.duration_hours:.0f} h"
    )
selected_index = st.selectbox(
    "Detected run",
    options=list(range(len(events))),
    format_func=lambda index: labels[index],
    key="swo_event_index",
)
event = events[selected_index]
event_start = pd.Timestamp(event.start_utc)
event_end = pd.Timestamp(event.end_utc)

ui.metric_cards(
    [
        {
            "label": "Peak Kp",
            "value": f"{event.peak_kp:.2f}",
            "delta": event.g_scale or "below G1",
            "caption": ui.format_ts(event.start_utc),
            "help": "Largest three-hour Kp sample inside this detected run.",
        },
        {
            "label": "Mean Kp",
            "value": f"{event.mean_kp:.2f}",
            "delta": f"threshold {event.threshold:g}",
            "caption": f"{event.sample_count} storm-level samples",
            "help": "Arithmetic mean of the samples at or above the threshold.",
        },
        {
            "label": "Sampled duration",
            "value": f"{event.duration_hours:.0f} h",
            "delta": f"{event.expected_samples} expected slots",
            "caption": "Last sample + one 3-hour interval",
            "help": (
                "Span of the sampled three-hour intervals, not the physical duration "
                "of the geomagnetic disturbance."
            ),
        },
        {
            "label": "Missing slots",
            "value": f"{event.missing_samples}",
            "delta": "inside run",
            "caption": f"status · {event.status}",
            "help": "Expected three-hour slots with no valid sample inside the run.",
        },
        {
            "label": "Source",
            "value": event.source.split(",")[0].strip(),
            "delta": event.status,
            "caption": "Kp producer",
            "help": "Kp source for the samples in this run. Mixed sources are possible.",
        },
    ]
)

pad = pd.Timedelta(hours=9)
focus_start = event_start - pad
focus_end = event_end + pad
focus = bundle.frame.loc[
    (pd.to_datetime(bundle.frame["time_utc"], utc=True) >= focus_start)
    & (pd.to_datetime(bundle.frame["time_utc"], utc=True) < focus_end)
]

st.subheader("Event window")
ui.show_plot(
    event_window_figure(
        focus,
        start=focus_start,
        end=focus_end,
        threshold=threshold,
    ),
    key="storm_event_timeline",
)
st.caption(
    "The shaded region marks the selected run. Neighbouring runs in the same window "
    "are shaded independently. Missing samples are gaps, not zeros."
)

st.subheader("Solar wind around the event")
show_wind = st.checkbox(
    "Load solar wind for this window",
    value=True,
    help=(
        "Recent windows use NOAA's propagated one-minute product; older windows "
        "use NASA OMNI2 hourly observations. Loading is skipped if unavailable."
    ),
)
if show_wind:
    try:
        with st.spinner("Loading solar-wind observations…"):
            wind_bundle = ui.cached_solar_wind(
                mode, focus_start.isoformat(), focus_end.isoformat()
            )
    except Exception as exc:
        wind_bundle = None
        st.warning(f"Solar wind unavailable for this window: {exc}")
    if wind_bundle is not None and not wind_bundle.frame.empty:
        ui.show_plot(
            solar_wind_figure(
                wind_bundle.frame,
                kp=focus,
                threshold=threshold,
                height=720,
            ),
            key="storm_solar_wind",
        )
        st.caption(
            f"{wind_bundle.message} Solar wind and Kp are shown on a shared UTC axis; "
            "they are not time-shifted to imply causation."
        )
    elif wind_bundle is not None:
        st.caption(
            "No solar-wind observations overlap this event in the selected mode. "
            "The bundled solar-wind sample covers May 2024 only."
        )

st.subheader("Observations in this run")
event_frame = bundle.frame.loc[
    (pd.to_datetime(bundle.frame["time_utc"], utc=True) >= event_start)
    & (pd.to_datetime(bundle.frame["time_utc"], utc=True) < event_end)
].copy()
event_display = event_frame.loc[:, ["time_utc", "kp", "a_running", "station_count", "status", "source"]]
event_display = event_display.assign(
    time_utc=pd.to_datetime(event_display["time_utc"], utc=True).dt.strftime(
        "%Y-%m-%d %H:%M"
    )
)
event_display = event_display.rename(
    columns={
        "time_utc": "Interval start (UTC)",
        "kp": "Kp",
        "a_running": "a running (nT)",
        "station_count": "Stations",
        "status": "Status",
        "source": "Source",
    }
)
st.dataframe(
    ui.display_frame(event_display),
    hide_index=True,
    width="stretch",
    column_config={
        "Kp": st.column_config.NumberColumn(format="%.2f"),
        "a running (nT)": st.column_config.NumberColumn(format="%d"),
    },
)

with st.expander("How this run was detected"):
    st.markdown(
        f"""
        - A run starts at the first valid sample with **Kp ≥ {threshold:g}** and ends
          after the last consecutive sample at or above the threshold.
        - One missing three-hour slot is allowed inside a run; two or more missing
          slots break it. This is an explicit convention, not a physical boundary.
        - The displayed end is the **last sample start plus three hours**.
        - G-scale labels use the official fixed bands (Kp 5 = G1 … Kp 9 = G5),
          independent of the threshold slider.
        - A threshold run is not an official NOAA storm event and does not capture
          the full lifetime of a geomagnetic disturbance.
        """
    )

st.divider()
st.subheader(f"All runs in this window ({len(events)})")
all_runs = events_to_frame(events).sort_values("start_utc")
all_display = pd.DataFrame(
    {
        "Start (UTC)": pd.to_datetime(all_runs["start_utc"]).dt.strftime(
            "%Y-%m-%d %H:%M"
        ),
        "End (UTC)": pd.to_datetime(all_runs["end_utc"]).dt.strftime(
            "%Y-%m-%d %H:%M"
        ),
        "Peak Kp": all_runs["peak_kp"].map(lambda value: f"{value:.2f}"),
        "G": all_runs["g_scale"].fillna("—"),
        "Hours": all_runs["duration_hours"].map(lambda value: f"{value:.0f}"),
        "Samples": all_runs["sample_count"].astype(int),
        "Missing": all_runs["missing_samples"].astype(int),
        "Status": all_runs["status"],
    }
)
st.dataframe(all_display, hide_index=True, width="stretch")

provenance = ui.provenance_for(
    bundle,
    threshold=threshold,
    transformations=[
        f"Detected contiguous Kp runs at or above {threshold:g}.",
        "Allowed one missing three-hour slot inside a run; two or more break it.",
        "Selected event window padded by nine hours on each side for context.",
    ],
    extra_notes={
        "selected_event_start_utc": event.start_utc.isoformat(),
        "selected_event_end_utc": event.end_utc.isoformat(),
        "selected_event_peak_kp": event.peak_kp,
    },
)
left, right = st.columns(2)
with left:
    ui.download_frame(
        event_frame,
        filename="space-weather-selected-run.csv",
        label="Download this run (CSV)",
        key="storm_event_csv",
    )
with right:
    ui.download_provenance(
        provenance,
        filename="space-weather-selected-run.provenance.json",
        key="storm_event_provenance",
    )
