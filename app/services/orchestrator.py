from __future__ import annotations
from pathlib import Path
from typing import Dict

from .distance_syncer import DistanceSyncer
from .messages_store import MessagesStore
import time

class SyncOrchestrator:
    def __init__(self, data_root: Path):
        self.root = Path(data_root)
        self.distance = DistanceSyncer(self.root)
        self.messages = MessagesStore(self.root)

    async def sync_all(self, session, course_id: int) -> Dict:
        """
        Sync distance, then emit messages for inserts/updates.
        """
        # Distance
        dist = await self.distance.sync_and_collect(session, course_id)

        # Emit/update messages
        now = int(time.time())
        for (kind, sname, old_gap, new_gap, sid) in dist["changes"]:
            if kind == "inserted":
                text = f"נוצר רישום פער מטרה ראשוני עבור {sname}: {new_gap}."
            else:
                if old_gap is None:
                    text = f"עדכון פער מטרה עבור {sname}: {new_gap}."
                else:
                    text = f"עדכון פער מטרה עבור {sname}: {old_gap} → {new_gap}."
            self.messages.upsert_message(
                course_id=course_id,
                db_type="distance",
                student_id=sid,
                student_name=sname,
                message=text,
                created_at=now,
            )

        return {
            "distance": dist,
            "messages_emitted": len(dist["changes"]),
        }

    def list_messages(self, course_id: int):
        return self.messages.list_all(course_id)

    async def run(self, session, course_id: int) -> Dict:
        """Backward compatible wrapper around :func:`sync_all`.

        The web application historically expected a ``run`` coroutine on the
        orchestrator instance.  The implementation was later renamed to
        ``sync_all`` but the debug endpoint still imports and calls ``run``.
        Providing this thin wrapper preserves the previous API and simply
        forwards the call to :func:`sync_all`.
        """
        return await self.sync_all(session, course_id)


def create_orchestrator() -> SyncOrchestrator:
    """Factory used by the web layer to lazily construct a synchronizer.

    The factory mirrors the global ``SYNC`` instance in ``app.webapp`` and is
    needed by the debug endpoint which imports ``create_orchestrator``.
    """
    from app.config import CONFIG

    return SyncOrchestrator(Path(CONFIG.data_root))
