"""Correlation Lab: associations and lags, with explicit statistical caveats."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from spaceweather import ui
from spaceweather.analysis.correlations import correlate, lagged_cross_correlation
from spaceweather.exceptions import InsufficientDataError
from spaceweather.visualization.distributions import lag_figure, scatter_figure

mode, threshold = ui.sidebar_controls()
start, end = ui.date_range_controls(mode)

ui.render_page_header(
    "Statistical exploration",
    "Correlation Lab",
    "Pair three-hour solar-wind aggregates with the Kp index. The lab reports "
    "sample size, autocorrelation-aware effective sample size, and confidence "
    "intervals — not just a headline coefficient.",
)

try:
    with st.spinner("Aligning Kp and solar wind on a shared three-hour grid…"):
        kp_bundle, wind_bundle, aligned = ui.cached_pair(
            mode, start.isoformat(), end.isoformat()
        )
except Exception as exc:
    st.error(f"Unable to load paired observations: {exc}")
    st.stop()

ui.render_status(kp_bundle)
st.caption(f"Solar wind: {wind_bundle.message}")

if aligned.empty:
    ui.empty_state(
        "No paired three-hour bins overlap this selection. The offline solar-wind "
        "sample covers May 2024 only; NOAA's propagated product covers about seven days."
    )
    st.stop()

aligned = aligned.copy()
aligned["abs_bz_nt"] = aligned["bz_gsm_nt"].abs()
variable_options = {
    "Speed (km/s)": ("speed_kms", "Solar-wind speed", "km/s"),
    "Density (p/cm³)": ("density_cm3", "Proton density", "protons/cm³"),
    "Bz (nT, GSM)": ("bz_gsm_nt", "IMF Bz", "nT"),
    "|Bz| (nT)": ("abs_bz_nt", "Absolute IMF Bz", "nT"),
    "|B| (nT)": ("bt_nt", "IMF magnitude", "nT"),
}
left, right = st.columns([2, 1])
with left:
    choice = st.selectbox(
        "Solar-wind variable",
        list(variable_options),
        key="correlation_variable",
        help="All solar-wind values are means over the same three-hour bins as Kp.",
    )
with right:
    max_lag = st.slider(
        "Lag search (+/− hours)",
        min_value=3,
        max_value=48,
        value=12,
        step=3,
        key="correlation_max_lag",
        help="Positive lag means the solar-wind variable leads Kp.",
    )
variable, variable_label, variable_unit = variable_options[str(choice)]

pairs = aligned.loc[:, ["time_utc", variable, "kp"]].dropna()
if len(pairs) < 3:
    ui.empty_state(
        f"Only {len(pairs)} paired observations are available for {variable_label}. "
        "At least three are required for a correlation."
    )
    st.stop()

try:
    result = correlate(aligned[variable], aligned["kp"])
except InsufficientDataError as exc:
    st.warning(str(exc))
    st.stop()

ui.metric_cards(
    [
        {
            "label": "Pearson r",
            "value": f"{result['pearson_r']:.3f}",
            "delta": f"95% CI {result['pearson_ci95_effective_low']:.2f} to "
            f"{result['pearson_ci95_effective_high']:.2f}",
            "caption": "CI uses effective n",
            "help": (
                "Linear correlation between paired three-hour aggregates. The "
                "confidence interval uses an autocorrelation-adjusted sample size."
            ),
        },
        {
            "label": "Spearman ρ",
            "value": f"{result['spearman_rho']:.3f}",
            "delta": f"p = {result['spearman_p']:.2g}",
            "caption": "Rank association",
            "help": "Monotonic association; less sensitive to extreme values than Pearson.",
        },
        {
            "label": "Paired bins",
            "value": f"{result['n']:,}",
            "delta": f"of {len(aligned):,} aligned",
            "caption": "Missing pairs excluded",
            "help": "Three-hour bins where both the wind variable and Kp are valid.",
        },
        {
            "label": "Effective n",
            "value": f"{result['n_effective']:.1f}",
            "delta": f"naive n = {result['n']:,}",
            "caption": "Autocorrelation-aware",
            "help": (
                "Serial correlation reduces the information content of overlapping "
                "observations. This estimate is used for the displayed CI."
            ),
        },
        {
            "label": "Naive 95% CI",
            "value": f"{result['pearson_ci95_naive_low']:.2f}–"
            f"{result['pearson_ci95_naive_high']:.2f}",
            "delta": "too narrow",
            "caption": "Shown for contrast",
            "help": (
                "A conventional independent-sample interval, shown only to make the "
                "effect of autocorrelation visible. Prefer the effective-n interval."
            ),
        },
    ]
)

st.markdown("")
left, right = st.columns([1.1, 1], gap="large")
with left:
    ui.show_plot(
        scatter_figure(
            aligned,
            x=variable,
            y="kp",
            x_label=f"{variable_label} ({variable_unit})",
            y_label="Kp index",
            title=f"{variable_label} versus Kp",
        ),
        key="correlation_scatter",
    )
    st.caption(
        f"{len(pairs):,} complete pairs. Point colour follows Kp; hover for the UTC "
        "timestamp. No regression line is drawn because neither variable is treated "
        "as an independent controlled input."
    )
with right:
    st.subheader("What this does and does not mean")
    st.markdown(
        """
        - Both variables are aggregated to the same **left-labelled three-hour
          bins**, matching the interval convention of Kp.
        - A high correlation is **association**, not evidence that this variable
          alone controls Kp.
        - Kp integrates many magnetospheric current systems; solar-wind coupling
          depends on speed, density, IMF orientation, and preconditioning.
        - p-values assume independent samples. The effective-n interval is the
          more honest uncertainty statement here.
        """
    )
    st.markdown(
        '<div class="swo-note">Treat this as exploratory analysis. Do not select a '
        "window because it produces a strong coefficient and then present it as a "
        "general result.</div>",
        unsafe_allow_html=True,
    )

st.divider()
st.subheader("Lagged association")
try:
    lag_frame = lagged_cross_correlation(
        aligned,
        x=variable,
        y="kp",
        max_lag_hours=float(max_lag),
        step_hours=3.0,
    )
except InsufficientDataError as exc:
    lag_frame = pd.DataFrame()
    st.warning(str(exc))

if lag_frame.empty:
    ui.empty_state(
        "Not enough paired observations to estimate lagged correlations with this window."
    )
else:
    ui.show_plot(
        lag_figure(
            lag_frame,
            title=f"{variable_label} versus Kp · lag scan",
        ),
        key="correlation_lag",
    )
    strongest = lag_frame.loc[lag_frame["r"].abs().idxmax()]
    direction = "leads" if float(strongest["lag_hours"]) > 0 else "lags"
    st.caption(
        f"Strongest absolute association in this scan: r = {strongest['r']:.3f} at "
        f"lag {strongest['lag_hours']:+.0f} h, where {variable_label} {direction} Kp. "
        "The lag scan is descriptive and does not establish a causal delay."
    )
    st.caption(
        "Positive lag means the solar-wind value at time t is compared with Kp at "
        "t + lag. Pairing always excludes missing values."
    )

provenance = ui.provenance_for(
    kp_bundle,
    threshold=threshold,
    transformations=[
        "Solar wind aggregated to left-labelled three-hour bins and inner-joined with Kp.",
        f"Correlation computed for {variable_label} and Kp; missing pairs excluded.",
        f"Lag scan from {-max_lag:+d} to {max_lag:+d} hours in three-hour steps.",
    ],
    extra_notes={
        "solar_wind_message": wind_bundle.message,
        "paired_bins": int(result["n"]),
        "effective_sample_size": result["n_effective"],
        "pearson_r": result["pearson_r"],
        "spearman_rho": result["spearman_rho"],
    },
)
left, right = st.columns(2)
with left:
    ui.download_frame(
        aligned,
        filename="space-weather-aligned-kp-solar-wind.csv",
        label="Download aligned pairs (CSV)",
        key="correlation_pairs_csv",
    )
with right:
    ui.download_provenance(
        provenance,
        filename="space-weather-correlation.provenance.json",
        key="correlation_provenance",
    )
