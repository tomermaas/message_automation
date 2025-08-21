# app/services/distance_syncer.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import sqlite3, json, hashlib

from app.db.storage import CourseStore

class DistanceSyncer:
    def __init__(self, data_root: Path):
        self.data_root = Path(data_root)

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS distances (
                course_id      INTEGER NOT NULL,
                student_id     TEXT    NOT NULL,
                student_name_he TEXT   NOT NULL,
                last_exam_date TEXT    NOT NULL,  -- DD-MM-YYYY as requested
                exam_name_he   TEXT    NOT NULL,
                target_score   TEXT    NOT NULL,
                total_score    TEXT    NOT NULL,
                PRIMARY KEY (course_id, student_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()

    def _hash_rows(self, rows: List[Dict[str, Any]]) -> str:
        payload = json.dumps(rows, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def sync(self, session, course_id: int) -> Dict[str, Any]:
        # Pull from API via the logged-in session
        data = await session.api_get_distance_details(course_id)

        # Normalize to the schema we store
        norm_rows = []
        for item in data or []:
            norm_rows.append({
                "course_id": int(course_id),
                "student_id": item.get("student_id", ""),
                "student_name_he": item.get("student_name", ""),  # already Hebrew
                "last_exam_date": item.get("last_exam_date", ""), # keep DD-MM-YYYY
                "exam_name_he": item.get("exam_name", ""),        # already Hebrew
                "target_score": item.get("target_score", ""),
                "total_score": item.get("total_score", ""),
            })

        # Open DB under data/courses/<teacher_id>/<course_id>/distance.sqlite
        store = CourseStore(Path(self.data_root), int(course_id), session.get_teacher_id())
        db_path = store.db_path("distance.sqlite")
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(db_path))
        try:
            self._ensure_schema(conn)
            cur = conn.cursor()

            # Change detection by content hash
            # (ignore constant course_id in the hash – it’s fixed per DB)
            hash_rows = [{k: v for k, v in r.items() if k != "course_id"} for r in norm_rows]
            new_hash = self._hash_rows(hash_rows)

            cur.execute("SELECT value FROM meta WHERE key=?", ("distance_hash",))
            row = cur.fetchone()
            old_hash = row[0] if row else None
            changed = (new_hash != old_hash)

            if changed:
                # Replace content for this course
                cur.execute("DELETE FROM distances WHERE course_id=?", (int(course_id),))
                cur.executemany("""
                    INSERT OR REPLACE INTO distances
                    (course_id, student_id, student_name_he, last_exam_date, exam_name_he, target_score, total_score)
                    VALUES (:course_id, :student_id, :student_name_he, :last_exam_date, :exam_name_he, :target_score, :total_score)
                """, norm_rows)

                if row:
                    cur.execute("UPDATE meta SET value=? WHERE key=?", (new_hash, "distance_hash"))
                else:
                    cur.execute("INSERT INTO meta(key,value) VALUES(?,?)", ("distance_hash", new_hash))

                conn.commit()

            return {
                "changed": changed,
                "rows": len(norm_rows),
                "db": str(db_path),
            }
        finally:
            conn.close()
