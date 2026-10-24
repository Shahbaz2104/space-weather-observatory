"""Shared design tokens for Plotly, Matplotlib, and Streamlit."""

from __future__ import annotations

from typing import Any, cast

import plotly.graph_objects as go
import plotly.io as pio

BG = "#070B16"
PANEL = "#10182A"
PANEL_ALT = "#0C1424"
CYAN = "#52F6E3"
VIOLET = "#9B87FF"
CORAL = "#FF5C7A"
TEXT = "#E8F0FF"
MUTED = "#8492AC"
GRID = "#24314A"
BORDER = "#22304A"
AMBER = "#FFC46B"
GREEN = "#6BE3A3"

COLOR_SEQUENCE = [CYAN, VIOLET, CORAL, AMBER, GREEN, "#7FB2FF", "#F58BD3"]
FONT_STACK = "Inter, 'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif"
MONO_STACK = "'JetBrains Mono', 'SFMono-Regular', Consolas, monospace"

HEATMAP_COLORSCALE = [
    [0.00, "#0A1220"],
    [0.18, "#11324D"],
    [0.42, "#1E6E82"],
    [0.62, CYAN],
    [0.80, VIOLET],
    [1.00, CORAL],
]

MPL_RC: dict[str, Any] = {
    "figure.facecolor": BG,
    "axes.facecolor": PANEL,
    "savefig.facecolor": BG,
    "axes.edgecolor": GRID,
    "axes.labelcolor": MUTED,
    "axes.titlecolor": TEXT,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "text.color": TEXT,
    "grid.color": GRID,
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 14,
    "axes.labelsize": 10,
    "legend.frameon": False,
}


def build_plotly_template() -> go.layout.Template:
    """Return the observatory Plotly template."""
    axis = {
        "gridcolor": GRID,
        "zerolinecolor": GRID,
        "linecolor": GRID,
        "tickcolor": GRID,
        "tickfont": {"color": MUTED, "size": 11},
        "title": {"font": {"color": MUTED, "size": 12}},
        "showline": False,
        "automargin": True,
    }
    return go.layout.Template(
        layout=go.Layout(
            paper_bgcolor=BG,
            plot_bgcolor=PANEL,
            font={"family": FONT_STACK, "color": TEXT, "size": 13},
            colorway=COLOR_SEQUENCE,
            title={
                "font": {"color": TEXT, "size": 18},
                "x": 0.01,
                "xanchor": "left",
            },
            margin={"l": 64, "r": 28, "t": 64, "b": 52},
            xaxis=axis,
            yaxis=axis,
            hoverlabel={
                "bgcolor": PANEL_ALT,
                "bordercolor": BORDER,
                "font": {"family": FONT_STACK, "color": TEXT, "size": 12},
            },
            legend={
                "bgcolor": "rgba(0,0,0,0)",
                "font": {"color": MUTED, "size": 11},
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
            },
            colorscale={"sequential": HEATMAP_COLORSCALE},
        )
    )


def register_plotly_template() -> None:
    """Register the template and make it the default for this process."""
    pio.templates["space_weather"] = build_plotly_template()
    pio.templates.default = "space_weather"


def apply_matplotlib_theme() -> None:
    """Apply the observatory theme to Matplotlib globally."""
    import matplotlib as mpl

    mpl.rcParams.update(cast(Any, MPL_RC))


def matplotlib_style() -> Any:
    """Return the rcParams dictionary for use in a context manager."""
    return dict(MPL_RC)
