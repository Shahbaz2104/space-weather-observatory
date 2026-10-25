"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings. Every field can be overridden with an ``SWO_`` variable."""

    model_config = SettingsConfigDict(
        env_prefix="SWO_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Space Weather Observatory"
    app_version: str = "0.1.0"
    data_dir: Path = PROJECT_ROOT / "data"
    raw_dir: Path = PROJECT_ROOT / "data" / "raw"
    processed_dir: Path = PROJECT_ROOT / "data" / "processed"
    sample_dir: Path = PROJECT_ROOT / "data" / "samples"
    cache_dir: Path = PROJECT_ROOT / "data" / "cache"
    output_dir: Path = PROJECT_ROOT / "output"
    assets_dir: Path = PROJECT_ROOT / "assets"

    kp_storm_threshold: float = Field(default=5.0, ge=0.0, le=9.0)
    http_timeout_seconds: float = Field(default=20.0, gt=0.0)
    http_retries: int = Field(default=3, ge=0, le=10)
    http_backoff_factor: float = Field(default=0.8, ge=0.0)
    cache_ttl_seconds: int = Field(default=900, ge=0)
    recent_kp_ttl_seconds: int = Field(default=900, ge=0)
    historical_ttl_seconds: int = Field(default=86_400, ge=0)
    offline_mode: bool = False

    max_animation_frames: int = Field(default=600, ge=10, le=10_000)
    default_animation_fps: int = Field(default=10, ge=1, le=60)
    default_animation_width: float = Field(default=12.0, gt=0.0)
    default_animation_height: float = Field(default=6.4, gt=0.0)
    default_animation_dpi: int = Field(default=100, ge=50, le=300)

    nasa_enabled: bool = False
    nasa_api_key: str | None = None
    nasa_timeout_seconds: float = Field(default=20.0, gt=0.0)

    recent_kp_url: str = (
        "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
    )
    solar_wind_speed_url: str = (
        "https://services.swpc.noaa.gov/products/summary/solar-wind-speed.json"
    )
    solar_wind_mag_url: str = (
        "https://services.swpc.noaa.gov/products/summary/solar-wind-mag-field.json"
    )
    propagated_solar_wind_url: str = (
        "https://services.swpc.noaa.gov/products/geospace/propagated-solar-wind.json"
    )
    gfz_kp_url: str = (
        "https://kp.gfz.de/fileadmin/files_for_gfz_cms/Kp_ap_since_1932.txt"
    )
    omni_url_template: str = (
        "https://spdf.gsfc.nasa.gov/pub/data/omni/low_res_omni/omni2_{year}.dat"
    )
    donki_base_url: str = "https://api.nasa.gov/DONKI"

    display_timezone: str = "UTC"

    def ensure_directories(self) -> None:
        """Create the writable directories used by the application."""
        for path in (
            self.data_dir,
            self.raw_dir,
            self.processed_dir,
            self.sample_dir,
            self.cache_dir,
            self.output_dir,
            self.assets_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
