"""Activity Heatmap: long-baseline geomagnetic rhythm."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from spaceweather import ui
from spaceweather.processing.cleaning import filter_time_range, valid_kp
from spaceweather.visualization.heatmaps import (
    aggregation_note,
    date_hour_figure,
    year_month_figure,
    year_month_matrix,
)

mode, threshold = ui.sidebar_controls()
start, end = ui.date_range_controls(mode)

ui.render_page_header(
    "Long baseline",
    "Geomagnetic activity heatmap",
    "Ninety years of Kp compressed into a calendar. Cells are means of valid "
    "three-hour observations; an empty cell means no observation, never zero.",
)

try:
    with st.spinner("Loading the historical Kp record…"):
        bundle = ui.cached_kp_historical(mode)
except Exception as exc:
    st.error(f"Unable to load historical Kp: {exc}")
    ui.empty_state("Switch to the offline sample or retry when the source is available.")
    st.stop()

ui.render_status(bundle)
if bundle.frame.empty:
    ui.empty_state("No historical Kp observations are available.")
    st.stop()

valid = valid_kp(bundle.frame)
times = pd.to_datetime(valid["time_utc"], utc=True)
storm_fraction = float((valid["kp"] >= threshold).mean() * 100.0)
ui.metric_cards(
    [
        {
            "label": "First observation",
            "value": times.min().strftime("%Y"),
            "delta": times.min().strftime("%d %b"),
            "caption": "Start of available record",
            "help": "Earliest valid Kp observation in the loaded historical record.",
        },
        {
            "label": "Last observation",
            "value": times.max().strftime("%Y"),
            "delta": times.max().strftime("%d %b"),
            "caption": "End of available record",
            "help": "Most recent valid Kp observation in the loaded historical record.",
        },
        {
            "label": "Valid observations",
            "value": f"{len(valid):,}",
            "delta": f"{times.dt.year.nunique()} calendar years",
            "caption": "Three-hour Kp samples",
            "help": "Rows with a usable Kp value. Missing values are excluded.",
        },
        {
            "label": "Mean Kp",
            "value": f"{valid['kp'].mean():.2f}",
            "delta": f"Kp ≥ {threshold:g}: {storm_fraction:.1f}%",
            "caption": "Descriptive only",
            "help": (
                "Arithmetic mean of valid Kp observations. The sampling and source "
                "mix are not uniform across the full record."
            ),
        },
    ]
)

st.caption(
    "GFZ Kp is a definitive, quality-controlled product for most of the record; "
    "recent values can still be preliminary. The offline sample covers selected "
    "years rather than the full baseline."
)

year_tab, window_tab, ranking_tab = st.tabs(
    ["Year × month", "Selected window · date × interval", "Stormiest years"]
)

with year_tab:
    ui.show_plot(year_month_figure(valid), key="heatmap_year_month")
    st.caption(aggregation_note())
    means, _ = year_month_matrix(valid)
    if not means.empty:
        export = means.copy()
        export.index.name = "year"
        export = export.reset_index()
        ui.download_frame(
            export,
            filename="space-weather-kp-year-month-means.csv",
            label="Download year × month means (CSV)",
            key="heatmap_year_month_csv",
        )

with window_tab:
    window = filter_time_range(bundle.frame, start, end)
    if window.empty:
        ui.empty_state(
            "The selected UTC window contains no Kp observations in this record. "
            "Widen the range in the sidebar."
        )
    else:
        ui.show_plot(date_hour_figure(window), key="heatmap_date_hour")
        st.caption(aggregation_note())
        ui.download_frame(
            window,
            filename="space-weather-kp-selected-window.csv",
            label="Download selected window (CSV)",
            key="heatmap_window_csv",
        )

with ranking_tab:
    yearly = (
        valid.assign(year=times.dt.year)
        .groupby("year", observed=True)["kp"]
        .agg(mean_kp="mean", peak_kp="max", samples="count")
        .reset_index()
    )
    yearly = yearly.loc[yearly["samples"] >= 2_000].sort_values(
        "mean_kp", ascending=False
    )
    if yearly.empty:
        ui.empty_state(
            "Not enough observations per year to rank years reliably in this record."
        )
    else:
        top = yearly.head(12).copy()
        top["mean_kp"] = top["mean_kp"].map(lambda value: f"{value:.2f}")
        top["peak_kp"] = top["peak_kp"].map(lambda value: f"{value:.2f}")
        top = top.rename(
            columns={
                "year": "Year",
                "mean_kp": "Mean Kp",
                "peak_kp": "Peak Kp",
                "samples": "Samples",
            }
        )
        st.dataframe(top, hide_index=True, width="stretch")
        st.caption(
            "Ranked by mean Kp for years with at least 2,000 valid three-hour "
            "observations. Solar-cycle phase and data coverage both influence the "
            "ranking; this is not a storm frequency index."
        )
        ui.download_frame(
            yearly,
            filename="space-weather-kp-yearly-summary.csv",
            label="Download yearly summary (CSV)",
            key="heatmap_yearly_csv",
        )

st.divider()
st.markdown(
    '<div class="swo-note">A heatmap is an aggregation, not a substitute for the '
    "underlying series. Hover any cell to see its mean and count, then open the "
    "Overview or Storm Explorer to inspect the observations themselves.</div>",
    unsafe_allow_html=True,
)
