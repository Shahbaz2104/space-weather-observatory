"""Methodology, provenance, and limitations."""

from __future__ import annotations

import streamlit as st

from spaceweather import ui

ui.render_page_header(
    "Scientific contract",
    "Methodology and limitations",
    "The rules behind every chart: where the numbers come from, how time and "
    "missing data are handled, and what the app deliberately refuses to claim.",
)

st.markdown(
    '<div class="swo-note">This is a research and education instrument. It is not '
    "an operational forecast, a civil-protection product, or a substitute for "
    "NOAA SWPC alerts. Observations can be preliminary and can be revised.</div>",
    unsafe_allow_html=True,
)

st.subheader("Sources")
st.dataframe(
    {
        "Provider": [
            "NOAA SWPC",
            "GFZ Helmholtz Centre for Geosciences",
            "NASA OMNIWeb / SPDF",
        ],
        "Product": [
            "Recent planetary Kp; propagated solar wind",
            "Kp and ap since 1932",
            "OMNI2 hourly IMF and solar wind",
        ],
        "Cadence": ["3-hour Kp; 1-minute wind", "3-hour", "1-hour"],
        "Status": [
            "Preliminary observations; propagated wind is modeled",
            "Definitive for most of the record; recent values can be preliminary",
            "Observed, time-shifted to Earth",
        ],
        "Terms": [
            "U.S. Government work; public domain",
            "CC BY 4.0",
            "NASA data usage guidance; attribution requested",
        ],
    },
    hide_index=True,
    width="stretch",
)

st.markdown(
    "- NOAA SWPC: https://www.swpc.noaa.gov/  \n"
    "- GFZ Kp: https://kp.gfz.de/  \n"
    "- NASA OMNIWeb: https://omniweb.gsfc.nasa.gov/"
)

with st.expander("How to cite the Kp data", expanded=False):
    st.markdown(
        "Matzka, J., Stolle, C., Yamazaki, Y., Bronkalla, O., & Morschhauser, A. "
        "(2021). *The geomagnetic Kp index and derived indices of geomagnetic "
        "activity.* Space Weather, 19, e2020SW002641. "
        "https://doi.org/10.1029/2020SW002641"
    )
    st.markdown(
        "GFZ Kp data are used under CC BY 4.0. Attribution is retained in the "
        "Methodology page, the app footer, and every provenance export."
    )

st.subheader("Time and interval conventions")
st.markdown(
    """
    - **All timestamps are UTC.** The interface never silently converts to local
      time.
    - A Kp timestamp marks the **start** of a three-hour interval. Kp at 00:00
      describes 00:00–03:00 UTC.
    - The selected end date is inclusive through 23:59:59 UTC.
    - Solar wind is aggregated onto **left-labelled** three-hour bins before it is
      joined with Kp. Both series therefore describe the same interval.
    - A small number of Kp files use a trailing interval label; the parsers do not
      shift timestamps. Source documentation governs the interpretation.
    """
)

st.subheader("Missing data")
st.markdown(
    """
    - Missing values stay missing. They are **not** zero-filled, interpolated, or
      forward-filled.
    - Lines in Plotly charts use `connectgaps=False`; a gap is visible as a gap.
    - Heatmap cells with no valid observation are absent, not zero.
    - Event detection allows at most **one** missing three-hour slot inside a run.
      Two or more missing slots break the run. This is a declared convention.
    - Completeness is valid observations divided by expected three-hour slots for
      the selected window.
    - Rows with invalid or out-of-range Kp are retained and flagged where the
      schema permits, so exports preserve the audit trail.
    """
)

st.subheader("Storm runs and G-scale labels")
st.markdown(
    """
    - A **detected run** is a contiguous sequence of valid Kp observations at or
      above the slider threshold. It is not an official NOAA storm catalog entry.
    - The sampled duration runs from the first sample start to the last sample
      start **plus three hours**. It is not the physical lifetime of the
      geomagnetic disturbance.
    - G-scale labels use the fixed NOAA bands: **Kp 5 = G1, 6 = G2, 7 = G3,
      8 = G4, 9 = G5**. Lowering the analysis threshold does not relabel G bands.
    - A single Kp 9 sample and a 24-hour Kp 5 run are different phenomena even
      though both are "storms"; use the peak, duration, and sample count together.
    """
)

st.subheader("Correlation and lag analysis")
st.markdown(
    """
    - Pearson and Spearman coefficients are computed only on complete pairs.
    - Three-hour Kp and solar-wind aggregates are serially correlated. The lab
      reports an **autocorrelation-aware effective sample size** and a Fisher
      confidence interval based on it.
    - The naive independent-sample interval is shown only to make the difference
      visible; it is too narrow for this kind of time series.
    - A lag scan compares x(t) with y(t + lag). Positive lag means x leads y.
      The scan is descriptive, not a causal test.
    - Window selection, multiple comparisons, and solar-cycle phase can all change
      a coefficient. Treat results as exploratory unless a pre-specified analysis
      supports them.
    """
)

st.subheader("Animation and exports")
st.markdown(
    """
    - Animations replay observed Kp in chronological order. No synthetic
      particles, interpolated measurements, or forecast frames are added.
    - A deterministic frame cap (600) and optional stride are reported in the
      preview metadata and provenance JSON.
    - Exports preserve ISO-8601 UTC timestamps, all rows in the selection, and the
      source/missing-data policy.
    - Provenance JSON records the software version, source URLs, retrieval times,
      units, transformations, and animation settings.
    - Generated media is written to `output/`, which is ignored by version
      control.
    """
)

st.subheader("Reproducibility")
st.code(
    """# Install
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"

# Rebuild the versioned sample and cached data
swo-fetch --refresh

# Run the dashboard
streamlit run app.py

# Quickstart export
swo-animate --format gif --threshold 5.0

# Quality gates
ruff check .
mypy
pytest
""",
    language="bash",
)

st.subheader("Known limitations")
st.markdown(
    """
    - NOAA's recent Kp product is preliminary and can be revised; GFZ definitive
      values may differ slightly.
    - The NOAA geospace solar-wind product is **propagated/modeled**, not a direct
      measurement at Earth. It is labeled as such in the interface.
    - The offline solar-wind sample covers **May 2024 only**; offline Kp covers
      2003 and 2024.
    - The app does not ingest DONKI flare/CME catalogs by default. The adapter
      exists but requires a NASA API key and is optional.
    - A 3D magnetosphere is intentionally deferred. This release prioritizes
      traceable two-dimensional evidence over visual speculation.
    - Browser rendering, font availability, and GIF playback vary by platform.
    - This tool cannot issue warnings, predict storm onset, or quantify local
      technological impacts.
    """
)

st.subheader("Attribution")
st.markdown(ui.source_attribution_markdown())

st.divider()
st.caption(
    "Every download carries provenance. If a claim cannot be traced to a source "
    "row and a transformation in that JSON, it does not belong in this app."
)
