"""Plotly timeline figures for Kp and solar-wind data."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from spaceweather.processing.cleaning import valid_kp
from spaceweather.processing.events import detect_events
from spaceweather.visualization import theme

EMPTY_MESSAGE = "No valid observations are available for the selected window."


def _date_ticks(start: pd.Timestamp, end: pd.Timestamp, max_ticks: int = 8) -> list[pd.Timestamp]:
    """Choose readable single-line date ticks for a window."""
    if end <= start:
        return [start]
    if end - start >= pd.Timedelta(days=2):
        candidate = pd.date_range(start.ceil("D"), end.floor("D"), freq="D")
        if len(candidate) >= 2:
            step = max(1, -(-len(candidate) // max_ticks))
            return list(candidate[::step])
    count = min(max_ticks, 6)
    return list(pd.date_range(start, end, periods=count))


def _empty_figure(title: str) -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(
        text=EMPTY_MESSAGE,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"color": theme.MUTED, "size": 13},
    )
    figure.update_layout(title=title, height=420)
    return figure


def kp_timeline_figure(
    frame: pd.DataFrame,
    *,
    threshold: float = 5.0,
    title: str = "Planetary Kp activity",
    height: int = 470,
    show_range_slider: bool = True,
) -> go.Figure:
    """Build the main Kp timeline with storm shading and threshold annotation."""
    valid = valid_kp(frame)
    if valid.empty:
        return _empty_figure(title)

    valid = valid.assign(time_utc=pd.to_datetime(valid["time_utc"], utc=True))
    min_time = valid["time_utc"].min()
    max_time = valid["time_utc"].max()
    grid = pd.date_range(min_time, max_time, freq="3h", tz="UTC")
    series = (
        valid.set_index("time_utc")
        .reindex(grid)
        .rename_axis("time_utc")
        .reset_index()
    )
    customdata = list(
        zip(
            series["source"].fillna("unknown"),
            series["status"].fillna("unknown"),
            series["time_utc"].dt.strftime("%Y-%m-%d %H:%M UTC"),
            strict=True,
        )
    )

    figure = go.Figure()
    for event in detect_events(valid, threshold=threshold):
        figure.add_vrect(
            x0=event.start_utc,
            x1=event.end_utc,
            fillcolor=theme.CORAL,
            opacity=0.07,
            line_width=0,
            layer="below",
        )

    figure.add_trace(
        go.Scatter(
            x=series["time_utc"],
            y=series["kp"],
            mode="lines+markers",
            name="Kp observation",
            line={"color": theme.CYAN, "width": 2.3},
            marker={"color": theme.CYAN, "size": 4.2},
            connectgaps=False,
            customdata=customdata,
            hovertemplate=(
                "%{customdata[2]}<br>"
                "Kp %{y:.2f}<br>"
                "Source: %{customdata[0]}<br>"
                "Status: %{customdata[1]}<extra></extra>"
            ),
        )
    )

    figure.add_hline(
        y=threshold,
        line={"color": theme.CORAL, "width": 1.2, "dash": "dash"},
        annotation_text=f"Storm threshold · Kp {threshold:g}",
        annotation_position="top left",
        annotation_yshift=7,
        annotation_font={"color": theme.CORAL, "size": 11},
    )

    peak_index = valid["kp"].idxmax()
    peak_row = valid.loc[peak_index]
    figure.add_trace(
        go.Scatter(
            x=[peak_row["time_utc"]],
            y=[peak_row["kp"]],
            mode="markers",
            name=f"Peak · Kp {peak_row['kp']:.2f}",
            marker={
                "color": theme.VIOLET,
                "size": 12,
                "symbol": "diamond",
                "line": {"color": theme.TEXT, "width": 1},
            },
            hovertemplate=(
                "Peak Kp %{y:.2f}<br>%{x|%Y-%m-%d %H:%M} UTC<extra></extra>"
            ),
        )
    )

    latest = valid.iloc[-1]
    figure.add_trace(
        go.Scatter(
            x=[latest["time_utc"]],
            y=[latest["kp"]],
            mode="markers",
            name="Latest",
            marker={
                "color": theme.CYAN,
                "size": 8,
                "line": {"color": theme.TEXT, "width": 1.5},
            },
            hovertemplate=(
                "Latest Kp %{y:.2f}<br>%{x|%Y-%m-%d %H:%M} UTC<extra></extra>"
            ),
        )
    )

    ticks = _date_ticks(min_time, max_time)
    figure.update_layout(
        title={"text": title},
        height=height,
        yaxis={
            "title": "Kp index (0–9)",
            "range": [0, 9.6],
            "dtick": 1,
        },
        xaxis={
            "title": "Time (UTC)",
            "tickmode": "array",
            "tickvals": ticks,
            "ticktext": [tick.strftime("%b %d") for tick in ticks],
            "hoverformat": "%Y-%m-%d %H:%M UTC",
            "rangeslider": {"visible": show_range_slider, "thickness": 0.07},
            "rangeselector": {
                "bgcolor": theme.PANEL_ALT,
                "activecolor": theme.VIOLET,
                "font": {"color": theme.MUTED, "size": 10},
                "buttons": [
                    {"count": 1, "label": "1D", "step": "day", "stepmode": "backward"},
                    {"count": 7, "label": "7D", "step": "day", "stepmode": "backward"},
                    {"count": 1, "label": "1M", "step": "month", "stepmode": "backward"},
                    {"step": "all", "label": "ALL"},
                ],
            },
        },
        hovermode="x",
        legend={"orientation": "h", "y": 1.04},
    )
    return figure


def solar_wind_figure(
    solar_wind: pd.DataFrame,
    *,
    kp: pd.DataFrame | None = None,
    threshold: float = 5.0,
    height: int = 700,
) -> go.Figure:
    """Linked solar-wind, IMF Bz, and Kp panels."""
    wind = solar_wind.copy()
    if wind.empty:
        return _empty_figure("Solar wind and geomagnetic activity")
    wind["time_utc"] = pd.to_datetime(wind["time_utc"], utc=True, errors="coerce")
    wind = wind.loc[wind["time_utc"].notna()].sort_values("time_utc")

    has_kp = kp is not None and not kp.empty
    rows = 3 if has_kp else 2
    titles = (
        ["Solar-wind speed (km/s)", "IMF Bz (nT, GSM)", "Planetary Kp"]
        if has_kp
        else ["Solar-wind speed (km/s)", "IMF Bz (nT, GSM)"]
    )
    figure = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        subplot_titles=titles,
    )

    figure.add_trace(
        go.Scatter(
            x=wind["time_utc"],
            y=wind["speed_kms"],
            name="Speed",
            line={"color": theme.CYAN, "width": 1.5},
            connectgaps=False,
            hovertemplate="%{x|%Y-%m-%d %H:%M} UTC<br>Speed %{y:.0f} km/s<extra></extra>",
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=wind["time_utc"],
            y=wind["bz_gsm_nt"],
            name="Bz (GSM)",
            line={"color": theme.VIOLET, "width": 1.3},
            connectgaps=False,
            hovertemplate="%{x|%Y-%m-%d %H:%M} UTC<br>Bz %{y:.1f} nT<extra></extra>",
        ),
        row=2,
        col=1,
    )
    figure.add_hline(
        y=0,
        line={"color": theme.MUTED, "width": 0.8, "dash": "dot"},
        row=2,
        col=1,
    )

    if has_kp:
        valid = valid_kp(kp)
        figure.add_trace(
            go.Scatter(
                x=valid["time_utc"],
                y=valid["kp"],
                name="Kp",
                line={"color": theme.CYAN, "width": 2.0},
                mode="lines+markers",
                marker={"size": 3.5, "color": theme.CYAN},
                connectgaps=False,
                hovertemplate=(
                    "%{x|%Y-%m-%d %H:%M} UTC<br>Kp %{y:.2f}<extra></extra>"
                ),
            ),
            row=3,
            col=1,
        )
        figure.add_hline(
            y=threshold,
            line={"color": theme.CORAL, "width": 1.1, "dash": "dash"},
            row=3,
            col=1,
        )
        figure.update_yaxes(title_text="Kp (0–9)", range=[0, 9.6], row=3, col=1)
    figure.update_yaxes(title_text="km/s", row=1, col=1)
    figure.update_yaxes(title_text="nT", row=2, col=1)
    figure.update_xaxes(title_text="Time (UTC)", row=rows, col=1)
    figure.update_layout(
        height=height,
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.05},
        margin={"t": 70},
    )
    for index in range(1, rows + 1):
        figure.update_xaxes(showgrid=True, row=index, col=1)
    figure.update_xaxes(
        rangeslider={"visible": True, "thickness": 0.05}, row=rows, col=1
    )
    return figure


def event_window_figure(
    frame: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    threshold: float = 5.0,
) -> go.Figure:
    """Focused Kp figure for one detected event."""
    window = frame.loc[
        (pd.to_datetime(frame["time_utc"], utc=True) >= start)
        & (pd.to_datetime(frame["time_utc"], utc=True) <= end)
    ]
    return kp_timeline_figure(
        window,
        threshold=threshold,
        title="Event detail",
        height=360,
        show_range_slider=False,
    )
