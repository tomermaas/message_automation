from app.services.messages_store import MessagesStore


def test_messages_store_upsert_and_list(tmp_path):
    store = MessagesStore(tmp_path)
    course_id = 7

    # insert message
    store.upsert_message(course_id, "distance", "s1", "Alice", "msg1", created_at=100)
    rows = store.list_all(course_id)
    assert rows == [
        {
            "id": rows[0]["id"],  # auto-generated
            "db_type": "distance",
            "student_id": "s1",
            "student_name": "Alice",
            "created_at": 100,
            "message": "msg1",
        }
    ]

    # update same message via helper
    updated = store.update_message(course_id, rows[0]["id"], "msg2")
    assert updated["message"] == "msg2"
    rows2 = store.list_all(course_id)
    assert len(rows2) == 1
    assert rows2[0]["message"] == "msg2"
    # created_at should remain unchanged
    assert rows2[0]["created_at"] == 100

    # add another type and ensure filtering/types work
    store.upsert_message(course_id, "other", "s2", "Bob", "m2", created_at=150)
    types = store.list_types(course_id)
    assert set(types) == {"distance", "other"}
    distance_only = store.list_all(course_id, msg_type="distance")
    assert len(distance_only) == 1
