from __future__ import annotations

from typing import Dict

import time
from sqlalchemy.engine import Engine

from app.config import CONFIG
from app.db.postgres_setup import ensure_teacher_schema, get_engine
from logic.messages import build_student_message
from .distance_syncer import DistanceSyncer
from .messages_store import MessagesStore


class SyncOrchestrator:
    def __init__(self, teacher_id: str, engine: Engine | None = None):
        self.teacher_id = str(teacher_id)
        self.engine = engine or get_engine(CONFIG.database_url)
        ensure_teacher_schema(self.engine, self.teacher_id)
        self.distance = DistanceSyncer(self.teacher_id, self.engine)
        self.messages = MessagesStore(self.teacher_id, self.engine)

    async def sync_all(self, session, course_id: int) -> Dict:
        """Sync distance data then emit messages for inserts/updates."""
        dist = await self.distance.sync_and_collect(session, course_id)
        now = int(time.time())
        for (kind, sname, ename, old_gap, new_gap, sid) in dist["changes"]:
            text = build_student_message(
                {
                    "kind": kind,
                    "student_name": sname,
                    "exam_name": ename,
                    "old_gap": old_gap,
                    "new_gap": new_gap,
                }
            )
            meta = self.distance.get_student(course_id, sid) or {}
            self.messages.upsert_message(
                course_id=course_id,
                db_type="distance",
                student_id=sid,
                student_name=sname,
                content_html=f"<p>{text}</p>",
                content_json={
                    "type": "doc",
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": text}]}
                    ],
                },
                meta=meta,
                created_at=now,
            )
        return {"distance": dist, "messages_emitted": len(dist["changes"])}

    def list_messages(
        self,
        course_id: int,
        msg_type: str | None = None,
        *,
        search: str | None = None,
        page: int = 1,
        limit: int = 30,
    ) -> Dict:
        return self.messages.list_all(
            course_id, msg_type=msg_type, search=search, page=page, limit=limit
        )

    def list_message_types(self, course_id: int):
        return self.messages.list_types(course_id)

    def update_message(
        self,
        course_id: int,
        msg_id: int,
        *,
        content_html: str,
        content_json: Dict,
    ):
        return self.messages.update_message(
            course_id, msg_id, content_html=content_html, content_json=content_json
        )

    async def run(self, session, course_id: int) -> Dict:
        """Backward compatible wrapper around :func:`sync_all`."""
        return await self.sync_all(session, course_id)


def create_orchestrator(teacher_id: str) -> SyncOrchestrator:
    """Factory used by the web layer to lazily construct a synchronizer."""
    engine = get_engine(CONFIG.database_url)
    return SyncOrchestrator(str(teacher_id), engine)
