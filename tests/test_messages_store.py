from app.services.messages_store import MessagesStore


def test_messages_store_upsert_and_list(tmp_path):
    store = MessagesStore(tmp_path)
    course_id = 7

    # insert message
    store.upsert_message(
        course_id=course_id,
        db_type="distance",
        student_id="s1",
        student_name="Alice",
        content_html="msg1",
        content_json={"type": "doc", "content": [{"type": "paragraph"}]},
        created_at=100,
    )
    rows = store.list_all(course_id)
    assert rows["total"] == 1
    msg = rows["rows"][0]
    assert msg["db_type"] == "distance"
    assert msg["student_id"] == "s1"
    assert msg["content_html"] == "msg1"
    assert msg["created_at"] == 100

    # update same message via helper
    updated = store.update_message(
        course_id,
        msg["id"],
        content_html="msg2",
        content_json={"type": "doc"},
    )
    assert updated["content_html"] == "msg2"
    rows2 = store.list_all(course_id)
    assert rows2["total"] == 1
    assert rows2["rows"][0]["content_html"] == "msg2"
    # created_at should remain unchanged
    assert rows2["rows"][0]["created_at"] == 100

    # add another type and ensure filtering/types work
    store.upsert_message(
        course_id=course_id,
        db_type="other",
        student_id="s2",
        student_name="Bob",
        content_html="m2",
        content_json={"type": "doc"},
        created_at=150,
    )
    types = store.list_types(course_id)
    assert set(types) == {"distance", "other"}
    distance_only = store.list_all(course_id, msg_type="distance")
    assert distance_only["total"] == 1
