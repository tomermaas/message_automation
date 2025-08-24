from app.services.messages_store import MessagesStore


def test_messages_store_upsert_and_list(tmp_path):
    store = MessagesStore(tmp_path)
    course_id = 7

    # insert message
    store.upsert_message(course_id, "distance", "s1", "Alice", "msg1", created_at=100)
    rows = store.list_all(course_id)
    assert rows == [
        {
            "db_type": "distance",
            "student_id": "s1",
            "student_name": "Alice",
            "created_at": 100,
            "message": "msg1",
        }
    ]

    # update same message
    store.upsert_message(course_id, "distance", "s1", "Alice", "msg2", created_at=200)
    rows2 = store.list_all(course_id)
    assert len(rows2) == 1
    assert rows2[0]["message"] == "msg2"
    assert rows2[0]["created_at"] == 200
