from app.db.storage import CourseStore


def test_course_store_paths(tmp_path):
    store = CourseStore(tmp_path, 5, "teacher")
    expected_base = tmp_path / "courses" / "teacher" / "5"
    assert store.base == expected_base
    assert store.db_path("foo.db") == expected_base / "foo.db"
