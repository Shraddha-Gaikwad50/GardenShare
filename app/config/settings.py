"""Runtime settings for the local GardenShare application."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_FILE = DATA_DIR / "gardenshare.db"


class Settings:
    """Simple in-process settings. No cloud services or secrets are used."""

    app_name: str = "GardenShare"
    app_version: str = "1.0.0"
    default_borrow_days: int = 14
    max_borrow_quantity: int = 50
    reminder_lead_days: int = 1
    database_filename: str = "gardenshare.db"

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def data_dir(self) -> Path:
        return DATA_DIR

    @property
    def database_path(self) -> Path:
        return DATABASE_FILE

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
