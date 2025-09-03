from __future__ import annotations

"""Helpers for managing the Postgres schema.

Each teacher gets a dedicated schema named ``teacher_<id>`` containing two
base tables:

* ``messages`` – stores per-student message content
* ``score_gap`` – tracks score gap information per student

Additional tables can be added under the teacher's schema in the future.
"""

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    Index,
    create_engine,
    text,
)
from sqlalchemy.engine import Engine


def get_engine(url: str) -> Engine:
    """Return a SQLAlchemy engine for ``url``.

    SQLAlchemy defaults to the legacy ``psycopg2`` driver when the scheme is
    ``postgresql://``.  The project depends on the newer ``psycopg`` driver, so
    upgrade the URL if no explicit driver is provided.
    """

    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    return create_engine(url, pool_pre_ping=True)


def ensure_teacher_schema(engine: Engine, teacher_id: str) -> None:
    """Ensure the per-teacher schema and base tables exist.

    ``teacher_id`` is incorporated into the schema name to isolate each
    teacher's data.  The function creates the schema if necessary and
    then creates ``messages`` and ``score_gap`` tables within it.
    """

    schema = f"teacher_{teacher_id}"
    conn = engine.connect()
    try:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        metadata = MetaData(schema=schema)

        Table(
            "messages",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("course_id", Integer, nullable=False),
            Column("db_type", String, nullable=False),
            Column("student_id", String, nullable=False),
            Column("student_name", String, nullable=False),
            Column("created_at", Integer, nullable=False),
            Column("updated_at", Integer, nullable=False),
            Column("content_html", Text, nullable=False),
            Column("content_json", Text, nullable=False),
            Column(
                "source",
                String,
                nullable=False,
                server_default=text("'auto'"),
            ),
            Column("meta", Text),
            UniqueConstraint(
                "course_id", "db_type", "student_id", name="uq_messages_key"
            ),
            Index("idx_messages_type", "course_id", "db_type"),
        )

        Table(
            "score_gap",
            metadata,
            Column("course_id", Integer, primary_key=True),
            Column("student_id", String, primary_key=True),
            Column("student_name", String),
            Column("last_exam_date", String),
            Column("exam_name", String),
            Column("target_score", String),
            Column("total_score", String),
            Column("gap", Integer),
            Column("gap_change", Integer),
        )

        metadata.create_all(conn)
    finally:
        close = getattr(conn, "close", None)
        if callable(close):
            close()
