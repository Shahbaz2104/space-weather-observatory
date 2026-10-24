"""Space Weather Observatory — Streamlit entry point."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from spaceweather import ui

st.set_page_config(
    page_title="Space Weather Observatory",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            "Space Weather Observatory — an evidence-first interpretation of "
            "geomagnetic activity. NOAA SWPC, GFZ Kp (CC BY 4.0), and NASA OMNI data."
        )
    },
)

ui.inject_css()

root = Path(__file__).resolve().parent
logo = root / "assets" / "logo.svg"
icon = root / "assets" / "icon.svg"
if logo.exists() and icon.exists():
    st.logo(str(logo), icon_image=str(icon), size="large")
elif logo.exists():
    st.logo(str(logo), size="large")

navigation = st.navigation(
    [
        st.Page(
            "pages/overview.py",
            title="Overview",
            icon=":material/dashboard:",
            default=True,
        ),
        st.Page(
            "pages/storm_explorer.py",
            title="Storm Explorer",
            icon=":material/bolt:",
        ),
        st.Page(
            "pages/heatmap.py",
            title="Activity Heatmap",
            icon=":material/grid_on:",
        ),
        st.Page(
            "pages/solar_wind.py",
            title="Solar Wind",
            icon=":material/air:",
        ),
        st.Page(
            "pages/correlation.py",
            title="Correlation Lab",
            icon=":material/query_stats:",
        ),
        st.Page(
            "pages/animation.py",
            title="Animation Studio",
            icon=":material/movie:",
        ),
        st.Page(
            "pages/methodology.py",
            title="Methodology",
            icon=":material/menu_book:",
        ),
    ],
    position="sidebar",
)
navigation.run()
ui.sidebar_footer()
