# app/db/handlers/distance_sqlite.py
from __future__ import annotations
import hashlib, json, sqlite3
from typing import Dict, Any, List, Tuple

from app.db.handlers.base import DataHandler
from app.db.storage import CourseStore
from automation.browser_async import AsyncKidumSession

def _to_hebrew(text: str | None) -> str:
    # Placeholder: API already provides Hebrew. If upstream ever sends other languages,
    # add your translation here (e.g., via your own service).
    return (text or "").strip()

class DistanceSqliteDB(DataHandler):
    """
    Stores per-course 'distance from target' rows in SQLite:
      columns: course_id, student_id, student_name_he, last_exam_date, exam_name_he, target_score, total_score
      PK: (course_id, student_id)
    Change detection: SHA256 across normalized rows.
    """
    kind = "distance_sqlite"

    def _ensure_schema(self, db_path: str) -> None:
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS distances (
                    course_id INTEGER NOT NULL,
                    student_id TEXT NOT NULL,
                    student_name_he TEXT,
                    last_exam_date TEXT,     -- DD-MM-YYYY (kept as-is)
                    exam_name_he TEXT,
                    target_score TEXT,
                    total_score TEXT,
                    PRIMARY KEY (course_id, student_id)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _normalize_rows(course_id: int, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        norm: List[Dict[str, Any]] = []
        for r in data or []:
            norm.append({
                "course_id": int(course_id),
                "student_id": str(r.get("student_id") or "").strip(),
                "student_name_he": _to_hebrew(r.get("student_name")),
                "last_exam_date": (r.get("last_exam_date") or "").strip(),  # already DD-MM-YYYY
                "exam_name_he": _to_hebrew(r.get("exam_name")),
                "target_score": (r.get("target_score") or "").strip(),
                "total_score": (r.get("total_score") or "").strip(),
            })
        # keep deterministic order for hashing
        norm.sort(key=lambda x: x["student_id"])
        return norm

    @staticmethod
    def _hash_rows(rows: List[Dict[str, Any]]) -> str:
        blob = json.dumps(rows, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def _upsert_batch(self, db_path: str, rows: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Returns (upserts_count, deletes_count) — deletes are done separately.
        """
        if not rows:
            return (0, 0)

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO distances (
                    course_id, student_id, student_name_he, last_exam_date, exam_name_he, target_score, total_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(course_id, student_id) DO UPDATE SET
                    student_name_he=excluded.student_name_he,
                    last_exam_date=excluded.last_exam_date,
                    exam_name_he=excluded.exam_name_he,
                    target_score=excluded.target_score,
                    total_score=excluded.total_score
            """, [
                (
                    r["course_id"],
                    r["student_id"],
                    r["student_name_he"],
                    r["last_exam_date"],
                    r["exam_name_he"],
                    r["target_score"],
                    r["total_score"],
                )
                for r in rows
            ])
            upserts = cur.rowcount if cur.rowcount is not None else 0
            conn.commit()
            return (upserts, 0)
        finally:
            conn.close()

    def _prune_missing(self, db_path: str, course_id: int, present_ids: List[str]) -> int:
        """
        Delete rows for this course_id whose student_id is NOT in present_ids.
        """
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            if present_ids:
                qmarks = ",".join("?" * len(present_ids))
                cur.execute(
                    f"DELETE FROM distances WHERE course_id=? AND student_id NOT IN ({qmarks})",
                    [course_id, *present_ids],
                )
            else:
                # If we have no rows at all, clear the course.
                cur.execute("DELETE FROM distances WHERE course_id=?", [course_id])
            deleted = cur.rowcount if cur.rowcount is not None else 0
            conn.commit()
            return deleted
        finally:
            conn.close()

    async def check_and_sync(self, session: AsyncKidumSession, course_id: int, store: CourseStore) -> Dict[str, Any]:
        raw = await session.api_get_distance_details(course_id)
        norm = self._normalize_rows(course_id, raw)
        new_hash = self._hash_rows(norm)

        meta_key = f"{self.kind}.hash"
        old_hash = store.get_meta_key(meta_key)

        if new_hash == old_hash:
            return {"changed": False, "details": "no change", "count": len(norm)}

        db_path = str(store.db_path("distance.sqlite"))
        self._ensure_schema(db_path)

        upserts, _ = self._upsert_batch(db_path, norm)
        deleted = self._prune_missing(db_path, int(course_id), [r["student_id"] for r in norm])

        store.set_meta_key(meta_key, new_hash)

        return {
            "changed": True,
            "details": "distance table updated",
            "upserts": upserts,
            "deleted": deleted,
            "count": len(norm),
        }
