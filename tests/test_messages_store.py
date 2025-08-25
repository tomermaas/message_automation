import sqlite3

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


def test_ensure_schema_upgrades_legacy_db(tmp_path):
    store = MessagesStore(tmp_path)
    course_id = 9

    # Manually create a legacy database missing the course_id column.
    db_path = store._db_path(course_id)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE messages (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            db_type       TEXT    NOT NULL,
            student_id    TEXT    NOT NULL,
            student_name  TEXT    NOT NULL,
            created_at    INTEGER NOT NULL,
            updated_at    INTEGER NOT NULL,
            content_html  TEXT    NOT NULL,
            content_json  TEXT    NOT NULL,
            source        TEXT    NOT NULL DEFAULT 'auto',
            meta          TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    # Trigger schema upgrade – should not raise even though the column is absent.
    assert store.list_types(course_id) == []

    # The migration should have added the course_id column.
    with sqlite3.connect(db_path) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(messages)")}
    assert "course_id" in cols


def test_ensure_schema_adds_updated_at(tmp_path):
    store = MessagesStore(tmp_path)
    course_id = 11

    # Create legacy database without the ``updated_at`` column.
    db_path = store._db_path(course_id)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE messages (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id     INTEGER NOT NULL,
            db_type       TEXT    NOT NULL,
            student_id    TEXT    NOT NULL,
            student_name  TEXT    NOT NULL,
            created_at    INTEGER NOT NULL,
            content_html  TEXT    NOT NULL,
            content_json  TEXT    NOT NULL,
            source        TEXT    NOT NULL DEFAULT 'auto',
            meta          TEXT
        )
        """,
    )
    # Insert a sample row so we can verify backfilling.
    conn.execute(
        """
        INSERT INTO messages (
            course_id, db_type, student_id, student_name,
            created_at, content_html, content_json, source, meta
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            course_id,
            "distance",
            "s1",
            "Alice",
            123,
            "html",
            "{}",
            "auto",
            "{}",
        ),
    )
    conn.commit()
    conn.close()

    # Listing messages should trigger the schema upgrade and succeed.
    rows = store.list_all(course_id)
    assert rows["total"] == 1
    assert rows["rows"][0]["updated_at"] == 123

    # ``updated_at`` column should now exist in the schema.
    with sqlite3.connect(db_path) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(messages)")}
    assert "updated_at" in cols
