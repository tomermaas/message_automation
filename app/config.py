from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List

def _parse_bool(env_name: str, default: bool) -> bool:
    raw = os.getenv(env_name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

def _default_cors_origins() -> List[str]:
    raw = os.getenv("CORS_ORIGINS", "http://127.0.0.1:8765,http://localhost:8765")
    # split + strip + drop empties
    return [o.strip() for o in raw.split(",") if o.strip()]

@dataclass
class _Config:
    base_url: str = os.getenv("KIDUM_BASE_URL", "https://kidum-me.com")
    headless: bool = _parse_bool("HEADLESS", True)
    cors_origins: List[str] = field(default_factory=_default_cors_origins)

CONFIG = _Config()
