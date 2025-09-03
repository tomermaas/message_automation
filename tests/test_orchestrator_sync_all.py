import asyncio
from contextlib import contextmanager

import pytest
from sqlalchemy import create_mock_engine

from app.services.orchestrator import SyncOrchestrator


class DummySession:
    pass


class DummyDistanceSyncer:
    schema = "teacher_t1"

    async def sync_and_collect(self, session, course_id):
        # No changes reported from the distance sync
        return {"inserted": 0, "updated": 0, "changes": []}

    def get_student(self, course_id, student_id):
        return {
            "student_name": "Alice",
            "exam_name": "Exam",
            "last_exam_date": None,
            "target_score": None,
            "total_score": None,
            "gap": 5,
            "gap_change": None,
        }

    def list_students(self, course_id):
        return [
            {
                "student_id": "s1",
                "student_name": "Alice",
                "exam_name": "Exam",
                "last_exam_date": None,
                "target_score": None,
                "total_score": None,
                "gap": 5,
                "gap_change": None,
            }
        ]


class DummyMessagesStore:
    def __init__(self):
        self.calls = []

    def upsert_message(self, **kwargs):
        self.calls.append(kwargs)

    def student_ids_with_messages(self, course_id, db_type="distance"):
        return set()


def make_engine():
    mock = create_mock_engine("postgresql://", executor=lambda *a, **k: None)

    class Engine:
        @contextmanager
        def begin(self):
            yield mock

    return Engine()


def test_sync_all_adds_message_for_missing_student():
    engine = make_engine()
    orch = SyncOrchestrator("t1", engine=engine)
    orch.distance = DummyDistanceSyncer()
    orch.messages = DummyMessagesStore()

    asyncio.run(orch.sync_all(DummySession(), course_id=1))

    assert len(orch.messages.calls) == 1
    assert orch.messages.calls[0]["student_id"] == "s1"
