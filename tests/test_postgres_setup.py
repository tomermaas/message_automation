from contextlib import contextmanager

from app.db.postgres_setup import ensure_teacher_schema
from sqlalchemy import create_mock_engine


def test_ensure_teacher_schema_emits_expected_sql():
    statements = []
    mock_conn = create_mock_engine(
        "postgresql://", executor=lambda sql, *m, **p: statements.append(str(sql))
    )

    class DummyEngine:
        @contextmanager
        def begin(self):
            yield mock_conn

    engine = DummyEngine()
    ensure_teacher_schema(engine, "t1")
    assert any("CREATE SCHEMA IF NOT EXISTS \"teacher_t1\"" in s for s in statements)
    assert any("teacher_t1.messages" in s for s in statements)
    assert any("teacher_t1.score_gap" in s for s in statements)
