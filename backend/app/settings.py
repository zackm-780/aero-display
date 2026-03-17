from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    open_sky_base_url: str = "https://opensky-network.org/api"
    open_sky_auth_url: str = (
        "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
    )
    open_sky_client_id: Optional[str] = None
    open_sky_client_secret: Optional[str] = None

    # Polling cadence (seconds) for the main OpenSky loop
    poll_interval_seconds: float = 10.0

    # Default center used when no state is persisted yet
    default_center_icao: str = "KSFO"

    # Default transition altitude in feet for FL formatting
    transition_altitude_ft: float = 18000.0

    # Paths can be overridden via environment; otherwise they resolve relative to repo
    data_dir: Optional[Path] = None
    frontend_dir: Optional[Path] = None

    @property
    def resolved_data_dir(self) -> Path:
        if self.data_dir is not None:
            return Path(self.data_dir).resolve()
        # default to backend/data relative to this file
        return Path(__file__).resolve().parents[1] / "data"

    @property
    def resolved_frontend_dir(self) -> Path:
        if self.frontend_dir is not None:
            return Path(self.frontend_dir).resolve()
        # default to frontend directory at repo root
        return Path(__file__).resolve().parents[2] / "frontend"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


