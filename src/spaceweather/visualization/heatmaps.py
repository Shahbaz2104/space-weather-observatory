"""Aggregation and rendering for geomagnetic heatmaps."""

from __future__ import annotations

import calendar

import pandas as pd
import plotly.graph_objects as go

from spaceweather.processing.cleaning import valid_kp
from spaceweather.visualization import theme

MONTH_LABELS = [calendar.month_abbr[index] for index in range(1, 13)]
HOUR_LABELS = [f"{hour:02d}:00" for hour in range(0, 24, 3)]


def date_hour_matrix(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Mean Kp by UTC date and three-hour interval, with sample counts.

    A cell is absent when no valid observation exists; it is not treated as zero.
    """
    valid = valid_kp(frame)
    if valid.empty:
        return pd.DataFrame(), pd.DataFrame()
    times = pd.to_datetime(valid["time_utc"], utc=True)
    working = valid.assign(date=times.dt.normalize(), hour=times.dt.hour)
    grouped = (
        working.groupby(["date", "hour"], observed=True)["kp"]
        .agg(["mean", "count"])
        .reset_index()
    )
    means = grouped.pivot(index="date", columns="hour", values="mean")
    counts = grouped.pivot(index="date", columns="hour", values="count")
    means = means.reindex(columns=range(0, 24, 3))
    counts = counts.reindex(columns=range(0, 24, 3))
    return means, counts


def year_month_matrix(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Mean Kp by calendar year and month, with sample counts."""
    valid = valid_kp(frame)
    if valid.empty:
        return pd.DataFrame(), pd.DataFrame()
    times = pd.to_datetime(valid["time_utc"], utc=True)
    working = valid.assign(year=times.dt.year, month=times.dt.month)
    grouped = (
        working.groupby(["year", "month"], observed=True)["kp"]
        .agg(["mean", "count"])
        .reset_index()
    )
    means = grouped.pivot(index="year", columns="month", values="mean")
    counts = grouped.pivot(index="year", columns="month", values="count")
    means = means.reindex(columns=range(1, 13))
    counts = counts.reindex(columns=range(1, 13))
    return means, counts


def _heatmap(
    means: pd.DataFrame,
    counts: pd.DataFrame,
    *,
    x_labels: list[str],
    y_labels: list[str],
    title: str,
    x_title: str,
    y_title: str,
    height: int,
) -> go.Figure:
    if means.empty:
        figure = go.Figure()
        figure.add_annotation(
            text="No valid observations for this aggregation.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"color": theme.MUTED, "size": 13},
        )
        figure.update_layout(title=title, height=height)
        return figure

    z_values = means.to_numpy(dtype=float)
    count_values = counts.to_numpy(dtype=float)
    custom = [
        [
            f"{int(count) if not pd.isna(count) else 0} observations"
            if not pd.isna(value)
            else "no valid observations"
            for value, count in zip(row, row_counts, strict=True)
        ]
        for row, row_counts in zip(z_values, count_values, strict=True)
    ]
    figure = go.Figure(
        go.Heatmap(
            z=z_values,
            x=x_labels[: len(means.columns)],
            y=y_labels[: len(means.index)],
            customdata=custom,
            colorscale=theme.HEATMAP_COLORSCALE,
            zmin=0,
            zmax=9,
            colorbar={
                "title": {"text": "Kp", "side": "top"},
                "tickfont": {"color": theme.MUTED, "size": 10},
                "outlinecolor": theme.GRID,
                "thickness": 12,
                "len": 0.75,
            },
            hovertemplate=(
                f"{y_title}: %{{y}}<br>{x_title}: %{{x}}<br>"
                "Mean Kp %{z:.2f}<br>%{customdata}<extra></extra>"
            ),
            hoverongaps=False,
            xgap=2,
            ygap=2,
        )
    )
    figure.update_layout(
        title=f"{title}<br><sup>Cell value = mean Kp · absent cells are missing, not zero</sup>",
        height=height,
        xaxis={"title": x_title, "type": "category", "side": "bottom"},
        yaxis={"title": y_title, "type": "category", "autorange": "reversed"},
        margin={"l": 80, "r": 30, "t": 84, "b": 50},
    )
    return figure


def date_hour_figure(frame: pd.DataFrame) -> go.Figure:
    """Render the date × UTC three-hour heatmap."""
    means, counts = date_hour_matrix(frame)
    y_labels = [timestamp.strftime("%Y-%m-%d") for timestamp in means.index]
    return _heatmap(
        means,
        counts,
        x_labels=HOUR_LABELS,
        y_labels=y_labels,
        title="Geomagnetic activity by date and UTC interval",
        x_title="UTC three-hour interval",
        y_title="Date (UTC)",
        height=max(420, min(900, 24 * len(means) + 160)),
    )


def year_month_figure(frame: pd.DataFrame) -> go.Figure:
    """Render the year × month heatmap."""
    means, counts = year_month_matrix(frame)
    y_labels = [str(int(year)) for year in means.index]
    return _heatmap(
        means,
        counts,
        x_labels=MONTH_LABELS,
        y_labels=y_labels,
        title="Geomagnetic activity by year and month",
        x_title="Month (UTC)",
        y_title="Year",
        height=max(380, min(900, 26 * len(means) + 180)),
    )


def aggregation_note() -> str:
    """Explain the aggregation rules shown next to the heatmap."""
    return (
        "Each cell is the arithmetic mean of valid three-hour Kp observations in "
        "that date/interval or year/month bucket. Counts are shown on hover. "
        "Empty cells mean no valid observation was available; they are not zero. "
        "Kp timestamps mark the start of the three-hour interval, so a value at "
        "00:00 covers 00:00–03:00 UTC."
    )
