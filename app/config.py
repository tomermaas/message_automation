# app/config.py
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List

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
    headless: bool = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")
    cors_origins: List[str] = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS", "http://127.0.0.1:8765,http://localhost:8765"
        ).split(",")
    )
    data_root: str = os.getenv("DATA_ROOT", "data")

CONFIG = _Config()
