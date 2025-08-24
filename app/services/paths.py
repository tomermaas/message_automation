# app/services/paths.py
from __future__ import annotations
from pathlib import Path
from app.config import CONFIG

def data_root() -> Path:
    return Path(CONFIG.data_root)

def course_dir(course_id: int) -> Path:
    p = data_root() / "courses" / str(int(course_id))
    p.mkdir(parents=True, exist_ok=True)
    return p

def distance_db_path(course_id: int) -> Path:
    fname = f"distance_{CONFIG.env}.db" if CONFIG.env else "distance.db"
    return course_dir(course_id) / fname

def messages_db_path(course_id: int) -> Path:
    fname = f"messages_{CONFIG.env}.db" if CONFIG.env else "messages.db"
    return course_dir(course_id) / fname
