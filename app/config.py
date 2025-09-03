# app/config.py
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List
from urllib.parse import urlparse
from dotenv import load_dotenv


def _get_database_url() -> str:
    """Return a sanitized database URL.

    The default ``.env`` file includes placeholder credentials
    (``user:pass``) which, if used verbatim, trigger authentication
    failures when connecting to Postgres.  Detect this case and fall
r
    back to a URL without credentials or host so that local
    environments relying on peer authentication over Unix sockets can
    function without embedding secrets.
    """

    raw = os.getenv("DATABASE_URL")
    if raw:
        parsed = urlparse(raw)
        if parsed.username == "user" and parsed.password == "pass":
            raw = None
    return raw or "postgresql+psycopg:///message_automation"

# Ensure variables from a local .env file are available before constructing the config
load_dotenv()

@dataclass
class _Config:
    base_url: str = (
        os.getenv("LMS_BASE_URL")
        or os.getenv("KIDUM_BASE_URL", "https://kidum-me.com")
    )
    api_base_url: str = (
        os.getenv("LMS_API_BASE_URL")
        or os.getenv("KIDUM_API_BASE_URL", "https://lmsapi.kidum-me.com")
    )
    database_url: str = field(default_factory=_get_database_url)
    headless: bool = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")
    cors_origins: List[str] = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS",
            "http://127.0.0.1:8765,http://localhost:8765,http://127.0.0.1:5173,http://localhost:5173",
        ).split(",")
    )
    data_root: str = os.getenv("DATA_ROOT", "data")
    env: str = os.getenv("APP_ENV", "")

    def __post_init__(self) -> None:
        """Ensure ``env`` reflects the current base URL.

        If ``APP_ENV`` is not provided, derive a stable environment name from
        the hostname.  This avoids collisions when running against different
        deployments and ensures debug routes read the correct database.
        """
        if not self.env:
            host = urlparse(self.base_url).netloc or "dev"
            # Replace characters that are problematic in filenames
            self.env = host.replace(":", "_").replace(".", "_")

CONFIG = _Config()
