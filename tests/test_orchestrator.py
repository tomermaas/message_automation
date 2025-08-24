import asyncio
from app.services.orchestrator import SyncOrchestrator

class DummySession:
    def __init__(self, data):
        self.data = data

    async def api_get_distance_details(self, course_id):
        return self.data


def test_sync_all(tmp_path, monkeypatch):
    monkeypatch.setattr('app.services.orchestrator.time.time', lambda: 111)

    session = DummySession([
        {"student_id": "s1", "student_name": "Alice", "gap": 3},
        {"student_id": "s2", "student_name": "Bob", "gap": 1},
    ])

    orchestrator = SyncOrchestrator(tmp_path)
    result = asyncio.run(orchestrator.sync_all(session, 1))

    assert result["distance"]["inserted"] == 2
    assert result["messages_emitted"] == 2

    messages = orchestrator.list_messages(1)
    assert len(messages) == 2
    assert all(m["created_at"] == 111 for m in messages)
