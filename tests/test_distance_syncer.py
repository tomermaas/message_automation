import asyncio
from app.services.distance_syncer import DistanceSyncer

class DummySession:
    def __init__(self, data):
        self.data = data

    async def api_get_distance_details(self, course_id):
        return self.data


def test_sync_and_collect(tmp_path):
    session = DummySession([
        {"student_id": "s1", "student_name": "Alice", "exam_name": "Math", "gap": 3},
        {"student_id": "s2", "student_name": "Bob", "exam_name": "Math", "gap": 2},
    ])
    syncer = DistanceSyncer(tmp_path)

    result1 = asyncio.run(syncer.sync_and_collect(session, 1))
    assert result1["inserted"] == 2
    assert result1["updated"] == 0
    assert len(result1["changes"]) == 2

    # Update one record
    session.data = [
        {"student_id": "s1", "student_name": "Alice", "exam_name": "Math", "gap": 5},
        {"student_id": "s2", "student_name": "Bob", "exam_name": "Math", "gap": 2},
    ]
    result2 = asyncio.run(syncer.sync_and_collect(session, 1))
    assert result2["inserted"] == 0
    assert result2["updated"] == 1
    change = result2["changes"][0]
    assert change[0] == "updated"
    assert change[1] == "Alice"
    assert change[3] == 3
    assert change[4] == 5
