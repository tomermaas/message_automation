from __future__ import annotations

"""Persistence layer for student messages.

This module stores per-course messages in a SQLite database.  The schema is
aligned with the requirements of the new Messages UI and keeps both the HTML
representation of the message and the TipTap JSON document used by the
frontend editor.  A JSON ``meta`` column is also available for arbitrary
type‑specific metadata (e.g. distance statistics).
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from app.config import CONFIG


class MessagesStore:
    """Light‑weight wrapper around a per‑course SQLite database."""

    def __init__(self, data_root: Path):
        self.root = Path(data_root)

    # ------------------------------------------------------------------
    # helpers
    def _db_path(self, course_id: int) -> Path:
        p = self.root / "courses" / str(course_id)
        p.mkdir(parents=True, exist_ok=True)
        fname = f"messages_{CONFIG.env}.db" if CONFIG.env else "messages.db"
        return p / fname

    def _conn(self, course_id: int) -> sqlite3.Connection:
        path = self._db_path(course_id)
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def ensure_schema(self, course_id: int) -> None:
        """Create the database schema if it does not yet exist."""

        with self._conn(course_id) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id     INTEGER NOT NULL,
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
                """,
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_unique ON messages(course_id, db_type, student_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(course_id, db_type)"
            )
            conn.commit()

    # ------------------------------------------------------------------
    # basic operations
    def upsert_message(
        self,
        *,
        course_id: int,
        db_type: str,
        student_id: str,
        student_name: str,
        content_html: str,
        content_json: Dict,
        source: str = "auto",
        meta: Optional[Dict] = None,
        created_at: Optional[int] = None,
    ) -> None:
        """Insert or update a message row.

        If a message already exists for the ``(course_id, db_type, student_id)``
        key the row is updated.  ``created_at`` is preserved on conflict to
        reflect the original timestamp while ``updated_at`` is always refreshed.
        Content is replaced only when ``source`` is ``"auto"`` on the existing
        row, allowing manual edits to persist across synchronisations.
        """

        self.ensure_schema(course_id)
        ts = int(time.time()) if created_at is None else created_at
        meta_json = json.dumps(meta or {}, ensure_ascii=False)
        content_json_str = json.dumps(content_json, ensure_ascii=False)

        with self._conn(course_id) as conn:
            conn.execute(
                """
                INSERT INTO messages (
                    course_id, db_type, student_id, student_name,
                    created_at, updated_at, content_html, content_json, source, meta
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(course_id, db_type, student_id) DO UPDATE SET
                    student_name=excluded.student_name,
                    updated_at=excluded.updated_at,
                    meta=excluded.meta,
                    content_html=CASE WHEN messages.source='auto' THEN excluded.content_html ELSE messages.content_html END,
                    content_json=CASE WHEN messages.source='auto' THEN excluded.content_json ELSE messages.content_json END,
                    source=CASE WHEN messages.source='auto' THEN excluded.source ELSE messages.source END
                """,
                (
                    course_id,
                    db_type,
                    student_id,
                    student_name,
                    ts,
                    ts,
                    content_html,
                    content_json_str,
                    source,
                    meta_json,
                ),
            )
            conn.commit()

    # ------------------------------------------------------------------
    def list_all(
        self,
        course_id: int,
        *,
        msg_type: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 30,
    ) -> Dict:
        """Return paginated messages for a course.

        The return value is a dictionary with ``rows`` and ``total`` entries.
        """

        self.ensure_schema(course_id)
        offset = max(page - 1, 0) * limit
        clauses: List[str] = ["course_id=?"]
        params: List[object] = [course_id]
        if msg_type and msg_type != "all":
            clauses.append("db_type=?")
            params.append(msg_type)
        if search:
            clauses.append("student_name LIKE ?")
            params.append(f"%{search}%")
        where = " AND ".join(clauses)

        base_query = (
            "SELECT id, course_id, db_type, student_id, student_name, created_at,"
            " updated_at, content_html, content_json, source, meta"
            " FROM messages WHERE " + where
        )

        with self._conn(course_id) as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM messages WHERE {where}", params
            ).fetchone()[0]
            rows = conn.execute(
                base_query + " ORDER BY student_name COLLATE NOCASE LIMIT ? OFFSET ?",
                (*params, limit, offset),
            ).fetchall()

        data: List[Dict] = []
        for row in rows:
            (
                mid,
                course_id,
                db_type,
                sid,
                sname,
                created_at,
                updated_at,
                html,
                json_str,
                source,
                meta_json,
            ) = row
            data.append(
                {
                    "id": mid,
                    "course_id": course_id,
                    "db_type": db_type,
                    "student_id": sid,
                    "student_name": sname,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "content_html": html,
                    "content_json": json.loads(json_str or "{}"),
                    "source": source,
                    "meta": json.loads(meta_json or "{}"),
                }
            )

        types_present = sorted({r[2] for r in rows})
        return {"rows": data, "total": total, "types_present": types_present}

    def list_types(self, course_id: int) -> List[str]:
        self.ensure_schema(course_id)
        with self._conn(course_id) as conn:
            rows = conn.execute(
                "SELECT DISTINCT db_type FROM messages WHERE course_id=? ORDER BY db_type",
                (course_id,),
            ).fetchall()
        return [r[0] for r in rows]

    def update_message(
        self,
        course_id: int,
        msg_id: int,
        *,
        content_html: str,
        content_json: Dict,
        source: str = "manual",
    ) -> Dict:
        """Update a message's content and return the updated row."""

        self.ensure_schema(course_id)
        now = int(time.time())
        json_str = json.dumps(content_json, ensure_ascii=False)
        with self._conn(course_id) as conn:
            cur = conn.execute(
                """
                UPDATE messages
                   SET content_html=?, content_json=?, updated_at=?, source=?
                 WHERE id=? AND course_id=?
                """,
                (content_html, json_str, now, source, msg_id, course_id),
            )
            if cur.rowcount == 0:
                raise KeyError(msg_id)
            conn.commit()
            row = conn.execute(
                "SELECT id, course_id, db_type, student_id, student_name, created_at,"
                " updated_at, content_html, content_json, source, meta"
                " FROM messages WHERE id=?",
                (msg_id,),
            ).fetchone()

        (
            mid,
            course_id,
            db_type,
            sid,
            sname,
            created_at,
            updated_at,
            html,
            json_str,
            source,
            meta_json,
        ) = row
        return {
            "id": mid,
            "course_id": course_id,
            "db_type": db_type,
            "student_id": sid,
            "student_name": sname,
            "created_at": created_at,
            "updated_at": updated_at,
            "content_html": html,
            "content_json": json.loads(json_str or "{}"),
            "source": source,
            "meta": json.loads(meta_json or "{}"),
        }

