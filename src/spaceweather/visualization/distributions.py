"""Distribution, scatter, and lag plots."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from spaceweather.processing.cleaning import valid_kp
from spaceweather.processing.resampling import (
    display_sampling_metadata,
    downsample_for_display,
)
from spaceweather.visualization import theme


def kp_histogram_figure(
    frame: pd.DataFrame,
    *,
    threshold: float = 5.0,
    title: str = "Distribution of observed Kp",
) -> go.Figure:
    """Histogram split into quiet and storm-level observations."""
    valid = valid_kp(frame)
    figure = go.Figure()
    if valid.empty:
        figure.add_annotation(
            text="No valid observations for this window.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"color": theme.MUTED},
        )
        figure.update_layout(title=title, height=380)
        return figure
    bins = {"start": 0.0, "end": 9.0, "size": 0.5}
    quiet = valid.loc[valid["kp"] < threshold, "kp"]
    storm = valid.loc[valid["kp"] >= threshold, "kp"]
    figure.add_trace(
        go.Histogram(
            x=quiet,
            xbins=bins,
            name=f"Below Kp {threshold:g}",
            marker={"color": theme.CYAN, "line": {"color": theme.PANEL, "width": 0.5}},
            opacity=0.9,
        )
    )
    figure.add_trace(
        go.Histogram(
            x=storm,
            xbins=bins,
            name=f"Kp ≥ {threshold:g}",
            marker={"color": theme.CORAL, "line": {"color": theme.PANEL, "width": 0.5}},
            opacity=0.95,
        )
    )
    figure.add_vline(
        x=threshold,
        line={"color": theme.CORAL, "width": 1.3, "dash": "dash"},
    )
    figure.update_layout(
        title=title,
        barmode="overlay",
        height=400,
        xaxis={"title": "Kp index", "range": [0, 9.2]},
        yaxis={"title": "Count of three-hour observations"},
        legend={"orientation": "h", "y": 1.04},
    )
    return figure


def scatter_figure(
    frame: pd.DataFrame,
    *,
    x: str,
    y: str,
    x_label: str,
    y_label: str,
    title: str,
    max_points: int | None = None,
) -> go.Figure:
    """Generic scatter with hover timestamps and missing pairs excluded."""
    if frame.empty or x not in frame or y not in frame:
        figure = go.Figure()
        figure.add_annotation(
            text="No paired observations are available.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"color": theme.MUTED},
        )
        figure.update_layout(title=title, height=440)
        return figure
    pairs = frame.dropna(subset=[x, y]).copy()
    if max_points is not None:
        pairs = downsample_for_display(pairs, max_points=max_points, value_columns=[x, y])
    custom = (
        pd.to_datetime(pairs["time_utc"], utc=True).dt.strftime("%Y-%m-%d %H:%M UTC")
        if "time_utc" in pairs
        else pd.Series([""] * len(pairs))
    )
    figure = go.Figure(
        go.Scattergl(
            x=pairs[x],
            y=pairs[y],
            mode="markers",
            marker={
                "color": pairs[y],
                "colorscale": theme.HEATMAP_COLORSCALE,
                "cmin": pairs[y].min(),
                "cmax": pairs[y].max(),
                "size": 6,
                "opacity": 0.65,
                "showscale": False,
            },
            customdata=custom,
            hovertemplate=(
                "%{customdata}<br>"
                f"{x_label}: %{{x:.2f}}<br>{y_label}: %{{y:.2f}}<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        title=title,
        height=460,
        xaxis={"title": x_label},
        yaxis={"title": y_label},
    )
    sampling = display_sampling_metadata(pairs)
    if sampling:
        figure.update_layout(meta=sampling)
    return figure


def lag_figure(lag_frame: pd.DataFrame, *, title: str = "Lagged cross-correlation") -> go.Figure:
    """Bar chart of correlation versus lag, with positive-lag meaning x leads y."""
    if lag_frame.empty:
        figure = go.Figure()
        figure.add_annotation(
            text="Not enough paired observations for lag analysis.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"color": theme.MUTED},
        )
        figure.update_layout(title=title, height=380)
        return figure
    colors = [
        theme.CYAN if value >= 0 else theme.VIOLET for value in lag_frame["r"]
    ]
    figure = go.Figure(
        go.Bar(
            x=lag_frame["lag_hours"],
            y=lag_frame["r"],
            marker={"color": colors},
            customdata=lag_frame[["n", "p_value"]],
            hovertemplate=(
                "Lag %{x:+.0f} h<br>r = %{y:.3f}<br>"
                "n = %{customdata[0]}<br>p = %{customdata[1]:.3g}<extra></extra>"
            ),
        )
    )
    figure.add_hline(y=0, line={"color": theme.MUTED, "width": 0.8})
    figure.update_layout(
        title=f"{title}<br><sup>Positive lag: x leads y</sup>",
        height=390,
        xaxis={"title": "Lag (hours)", "dtick": 3},
        yaxis={"title": "Pearson r", "range": [-1, 1]},
    )
    return figure
