# app/db/handlers/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any
from app.db.storage import CourseStore
from automation.api_client import KidumApiSession

class DataHandler(ABC):
    """
    A “database” (handler) for a course. Each handler:
      - fetches remote snapshot for the selected course
      - checks if something changed (your choice: hash, version, timestamps, etc.)
      - applies its own storage/update logic (sqlite/json/files...)
    """
    kind: str  # unique id, e.g. "course_info_sqlite"

    @abstractmethod
    async def check_and_sync(
        self,
        session: KidumApiSession,
        course_id: int,
        store: CourseStore
    ) -> Dict[str, Any]:
        """
        Returns a dict like:
          { "changed": bool, "details": "...", ... }
        Implement change detection and storage here.
        """
        raise NotImplementedError
