# app/db/storage.py
from __future__ import annotations
from pathlib import Path

class CourseStore:
    """
    Resolves per-course storage locations:
      <data_root>/courses/<teacher_id>/<course_id>/
    """
    def __init__(self, root: Path, course_id: int, teacher_id: str):
        self.root = Path(root)
        self.course_id = int(course_id)
        self.teacher_id = teacher_id

    @property
    def base(self) -> Path:
        return self.root / "courses" / str(self.teacher_id) / str(self.course_id)

    def db_path(self, filename: str) -> Path:
        return self.base / filename
