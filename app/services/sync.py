# app/services/sync.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any

from app.services.distance_syncer import DistanceSyncer

class SyncOrchestrator:
    def __init__(self, data_root: Path):
        self.data_root = Path(data_root)

    async def run(self, session, course_id: int) -> Dict[str, Any]:
        """
        Runs all sync tasks for the selected course.
        Add more syncers here in the future.
        """
        out: Dict[str, Any] = {}
        distance = DistanceSyncer(self.data_root)
        out["distance"] = await distance.sync(session, int(course_id))
        return out
