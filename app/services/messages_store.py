from __future__ import annotations
import sqlite3, time
from pathlib import Path
from typing import List, Dict, Optional
from app.config import CONFIG


class MessagesStore:
    def __init__(self, data_root: Path):
        self.root = Path(data_root)

    def _db_path(self, course_id: int) -> Path:
        p = self.root / "courses" / str(course_id)
        p.mkdir(parents=True, exist_ok=True)
        fname = f"messages_{CONFIG.env}.db" if CONFIG.env else "messages.db"
        return p / fname

    def _conn(self, course_id: int):
        path = self._db_path(course_id)
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def ensure_schema(self, course_id: int):
        with self._conn(course_id) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    db_type TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    student_name TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    UNIQUE(db_type, student_id)
                )
                """,
            )
            conn.commit()

    def upsert_message(
        self,
        course_id: int,
        db_type: str,
        student_id: str,
        student_name: str,
        message: str,
        created_at: Optional[int] = None,
    ):
        self.ensure_schema(course_id)
        ts = int(time.time()) if created_at is None else created_at
        with self._conn(course_id) as conn:
            conn.execute(
                """
                INSERT INTO messages (db_type, student_id, student_name, created_at, message)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(db_type, student_id) DO UPDATE SET
                    student_name=excluded.student_name,
                    created_at=excluded.created_at,
                    message=excluded.message
                """,
                (db_type, student_id, student_name, ts, message),
            )
            conn.commit()

    def list_all(self, course_id: int, msg_type: Optional[str] = None) -> List[Dict]:
        """Return messages for a course, optionally filtered by type."""

        self.ensure_schema(course_id)
        query = (
            "SELECT id, db_type, student_id, student_name, created_at, message "
            "FROM messages"
        )
        params: List[object] = []
        if msg_type and msg_type != "all":
            query += " WHERE db_type=?"
            params.append(msg_type)
        query += " ORDER BY created_at DESC"

        with self._conn(course_id) as conn:
            rows = conn.execute(query, params).fetchall()

        out: List[Dict] = []
        for (mid, db_type, sid, sname, created_at, msg) in rows:
            out.append(
                {
                    "id": mid,
                    "db_type": db_type,
                    "student_id": sid,
                    "student_name": sname,
                    "created_at": created_at,
                    "message": msg,
                }
            )
        return out

    def list_types(self, course_id: int) -> List[str]:
        """Return distinct message types for the course."""

        self.ensure_schema(course_id)
        with self._conn(course_id) as conn:
            rows = conn.execute(
                "SELECT DISTINCT db_type FROM messages ORDER BY db_type"
            ).fetchall()
        return [r[0] for r in rows]

    def update_message(self, course_id: int, msg_id: int, message: str) -> Dict:
        """Update only the ``message`` field for a row and return the updated row."""

        self.ensure_schema(course_id)
        with self._conn(course_id) as conn:
            cur = conn.execute(
                "UPDATE messages SET message=? WHERE id=?",
                (message, msg_id),
            )
            if cur.rowcount == 0:
                raise KeyError(msg_id)
            conn.commit()
            row = conn.execute(
                "SELECT id, db_type, student_id, student_name, created_at, message FROM messages WHERE id=?",
                (msg_id,),
            ).fetchone()

        return {
            "id": row[0],
            "db_type": row[1],
            "student_id": row[2],
            "student_name": row[3],
            "created_at": row[4],
            "message": row[5],
        }
