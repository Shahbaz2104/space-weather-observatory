"""Smoke-test the Streamlit entry point and each page in offline mode."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from spaceweather.config import get_settings

ROOT = Path(__file__).resolve().parents[2]
ANIMATION_PAGE = ROOT / "pages" / "animation.py"
OFFLINE_LABEL = "Offline sample — versioned observations"
SCRIPTS = [
    "app.py",
    "pages/overview.py",
    "pages/storm_explorer.py",
    "pages/heatmap.py",
    "pages/solar_wind.py",
    "pages/correlation.py",
    "pages/animation.py",
    "pages/methodology.py",
]


@pytest.fixture(autouse=True)
def _offline_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("SWO_OFFLINE_MODE", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _render_offline(path: Path) -> AppTest:
    app = AppTest.from_file(str(path), default_timeout=120)
    app.run()
    if len(app.sidebar.radio):
        app.sidebar.radio[0].set_value(OFFLINE_LABEL)
        app.run()
    return app


@pytest.mark.integration
@pytest.mark.parametrize("script", SCRIPTS)
def test_script_renders_without_exceptions(script: str) -> None:
    app = _render_offline(ROOT / script)
    assert not list(app.exception)


@pytest.mark.integration
def test_overview_discloses_display_downsampling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SWO_DISPLAY_MAX_POINTS", "100")
    get_settings.cache_clear()

    app = _render_offline(ROOT / "pages" / "overview.py")

    assert not list(app.exception)
    assert any("downsample" in caption.value.lower() for caption in app.caption)


@pytest.mark.integration
def test_animation_page_uses_configured_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SWO_DEFAULT_ANIMATION_FPS", "18")
    monkeypatch.setenv("SWO_DEFAULT_ANIMATION_WIDTH", "14.5")
    monkeypatch.setenv("SWO_DEFAULT_ANIMATION_HEIGHT", "7.5")
    monkeypatch.setenv("SWO_DEFAULT_ANIMATION_DPI", "120")
    monkeypatch.setenv("SWO_MAX_ANIMATION_FRAMES", "321")
    get_settings.cache_clear()

    app = _render_offline(ANIMATION_PAGE)

    assert not list(app.exception)
    sliders = {slider.label: slider.value for slider in app.slider}
    assert sliders["Frames per second"] == 18
    assert sliders["Figure width (inches)"] == 14.5
    assert sliders["Figure height (inches)"] == 7.5
    assert app.select_slider[0].value == 120
    assert any("capped at 321 frames" in caption.value for caption in app.caption)
