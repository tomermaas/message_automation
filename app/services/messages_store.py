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
                """
            )
            conn.commit()

    def upsert_message(self, course_id: int, db_type: str, student_id: str, student_name: str, message: str, created_at: Optional[int] = None):
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

    def list_all(self, course_id: int) -> List[Dict]:
        self.ensure_schema(course_id)
        with self._conn(course_id) as conn:
            rows = conn.execute(
                "SELECT db_type, student_id, student_name, created_at, message FROM messages ORDER BY created_at DESC"
            ).fetchall()
        out = []
        for (db_type, sid, sname, created_at, msg) in rows:
            out.append({
                "db_type": db_type,
                "student_id": sid,
                "student_name": sname,
                "created_at": created_at,
                "message": msg,
            })
        return out
