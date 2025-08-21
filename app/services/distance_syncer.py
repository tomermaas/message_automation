# app/services/distance_syncer.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Optional
import sqlite3, json, hashlib

from app.db.storage import CourseStore

class DistanceSyncer:
    def __init__(self, data_root: Path):
        self.data_root = Path(data_root)

    # ---------- schema & migration ----------
    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        cur = conn.cursor()
        # Base table (original + new columns)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS distances (
                course_id        INTEGER NOT NULL,
                student_id       TEXT    NOT NULL,
                student_name_he  TEXT    NOT NULL,
                last_exam_date   TEXT    NOT NULL,  -- DD-MM-YYYY
                exam_name_he     TEXT    NOT NULL,
                target_score     TEXT    NOT NULL,
                total_score      TEXT    NOT NULL,
                gap              INTEGER NOT NULL DEFAULT 0,
                gap_cahnge       INTEGER NULL,
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

        # Idempotent migration for older DBs
        cols = self._get_columns(conn, "distances")
        if "gap" not in cols:
            cur.execute("ALTER TABLE distances ADD COLUMN gap INTEGER NOT NULL DEFAULT 0")
        if "gap_cahnge" not in cols:
            cur.execute("ALTER TABLE distances ADD COLUMN gap_cahnge INTEGER NULL")
        conn.commit()

    def _get_columns(self, conn: sqlite3.Connection, table: str) -> List[str]:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        return [r[1] for r in cur.fetchall()]

    # ---------- hashing ----------
    def _hash_rows(self, rows: List[Dict[str, Any]]) -> str:
        """
        Hash only the upstream content (ignore course_id and the derived gap_cahnge field).
        """
        # Strip fields that are local/derived
        sanitized = []
        for r in rows:
            x = dict(r)
            x.pop("course_id", None)
            x.pop("gap_cahnge", None)
            sanitized.append(x)
        payload = json.dumps(sanitized, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ---------- load existing ----------
    def _load_existing_by_student(self, conn: sqlite3.Connection, course_id: int) -> Dict[str, Dict[str, Any]]:
        cur = conn.cursor()
        cur.execute("""
            SELECT student_id, student_name_he, last_exam_date, exam_name_he,
                   target_score, total_score, gap
            FROM distances
            WHERE course_id=?
        """, (int(course_id),))
        out: Dict[str, Dict[str, Any]] = {}
        for row in cur.fetchall():
            out[row[0]] = {
                "student_id": row[0],
                "student_name_he": row[1],
                "last_exam_date": row[2],
                "exam_name_he": row[3],
                "target_score": row[4],
                "total_score": row[5],
                "gap": int(row[6]) if row[6] is not None else 0,
            }
        return out

    def _row_changed(self, new_row: Dict[str, Any], old_row: Optional[Dict[str, Any]]) -> bool:
        if old_row is None:
            return True
        # Compare all upstream columns including gap
        keys = ["student_name_he", "last_exam_date", "exam_name_he", "target_score", "total_score", "gap"]
        return any(new_row.get(k) != old_row.get(k) for k in keys)

    # ---------- sync ----------
    async def sync(self, session, course_id: int) -> Dict[str, Any]:
        # Pull upstream
        data = await session.api_get_distance_details(course_id)

        # Normalize to our schema
        norm_rows: List[Dict[str, Any]] = []
        for item in data or []:
            norm_rows.append({
                "course_id": int(course_id),
                "student_id": item.get("student_id", ""),
                "student_name_he": item.get("student_name", ""),  # already Hebrew
                "last_exam_date": item.get("last_exam_date", ""), # keep DD-MM-YYYY
                "exam_name_he": item.get("exam_name", ""),        # already Hebrew
                "target_score": item.get("target_score", ""),
                "total_score": item.get("total_score", ""),
                "gap": int(item.get("gap", 0) or 0),
                "gap_cahnge": None,  # filled only if row actually changes
            })

        # DB path
        store = CourseStore(Path(self.data_root), int(course_id), session.get_teacher_id())
        db_path = store.db_path("distance.sqlite")
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(db_path))
        try:
            self._ensure_schema(conn)
            cur = conn.cursor()

            # Global change detection (dataset level)
            new_hash = self._hash_rows(norm_rows)
            cur.execute("SELECT value FROM meta WHERE key=?", ("distance_hash",))
            row = cur.fetchone()
            old_hash = row[0] if row else None
            dataset_changed = (new_hash != old_hash)

            if not dataset_changed:
                return {"changed": False, "rows": len(norm_rows), "db": str(db_path)}

            # Per-row comparison for gap_cahnge calculation
            existing = self._load_existing_by_student(conn, int(course_id))
            # Fill gap_cahnge only if row changed
            for r in norm_rows:
                prev = existing.get(r["student_id"])
                if self._row_changed(r, prev):
                    # Only compute delta if we have a known old gap
                    if prev is not None and "gap" in prev and prev["gap"] is not None:
                        r["gap_cahnge"] = r["gap"] - int(prev["gap"])
                    else:
                        r["gap_cahnge"] = None
                else:
                    r["gap_cahnge"] = None

            # Replace course content (keeps DB clean if students disappear)
            cur.execute("DELETE FROM distances WHERE course_id=?", (int(course_id),))
            cur.executemany("""
                INSERT OR REPLACE INTO distances
                (course_id, student_id, student_name_he, last_exam_date, exam_name_he,
                 target_score, total_score, gap, gap_cahnge)
                VALUES (:course_id, :student_id, :student_name_he, :last_exam_date, :exam_name_he,
                        :target_score, :total_score, :gap, :gap_cahnge)
            """, norm_rows)

            if row:
                cur.execute("UPDATE meta SET value=? WHERE key=?", (new_hash, "distance_hash"))
            else:
                cur.execute("INSERT INTO meta(key,value) VALUES(?,?)", ("distance_hash", new_hash))

            conn.commit()
            return {"changed": True, "rows": len(norm_rows), "db": str(db_path)}
        finally:
            conn.close()
