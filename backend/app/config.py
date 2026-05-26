"""Application configuration from environment variables."""

import os
from functools import lru_cache
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_SQLITE_URL = f"sqlite:///{(_BACKEND_DIR / 'vuln_mgmt.db').as_posix()}"


class Settings:
    """Runtime settings loaded from environment."""

    APP_NAME: str = "Vulnerability Management Platform"
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    DATABASE_URL: str = os.getenv("DATABASE_URL", _DEFAULT_SQLITE_URL)

    NVD_API_KEY: str | None = os.getenv("NVD_API_KEY")
    NVD_SYNC_DAYS: int = int(os.getenv("NVD_SYNC_DAYS", "7"))
    NVD_MAX_RESULTS: int = int(os.getenv("NVD_MAX_RESULTS", "100"))

    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production-min-32")
    ALLOWED_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000",
        ).split(",")
        if o.strip()
    ]

    TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str | None = os.getenv("TELEGRAM_CHAT_ID")

    # SLA days by priority
    SLA_DAYS: dict[str, int] = {
        "critical": 7,
        "high": 14,
        "medium": 30,
        "low": 90,
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
