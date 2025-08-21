from __future__ import annotations
import os
from dataclasses import dataclass

# dotenv is optional; if not installed/used, this safely no-ops
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

@dataclass(frozen=True)
class Config:
    base_url: str = os.getenv("KIDUM_BASE_URL", "https://kidum-me.com")
    headless: bool = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"

CONFIG = Config()
