from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from app.config import CONFIG

class DistanceSyncer:
    """
    Maintains distance.db and returns changes (inserted/updated)
    """
    def __init__(self, data_root: Path):
        self.root = Path(data_root)

    def _db_path(self, course_id: int) -> Path:
        p = self.root / "courses" / str(course_id)
        p.mkdir(parents=True, exist_ok=True)
        fname = f"distance_{CONFIG.env}.db" if CONFIG.env else "distance.db"
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
                CREATE TABLE IF NOT EXISTS distance (
                    student_id TEXT PRIMARY KEY,
                    student_name TEXT NOT NULL,
                    last_exam_date TEXT,
                    exam_name TEXT,
                    target_score TEXT,
                    total_score TEXT,
                    gap INTEGER,
                    gap_change INTEGER
                )
                """
            )
            conn.commit()

    def _select_existing(self, conn, student_id: str) -> Optional[Dict]:
        row = conn.execute(
            "SELECT student_name, last_exam_date, exam_name, target_score, total_score, gap, gap_change FROM distance WHERE student_id=?",
            (student_id,),
        ).fetchone()
        if not row:
            return None
        (student_name, last_exam_date, exam_name, target_score, total_score, gap, gap_change) = row
        return {
            "student_name": student_name,
            "last_exam_date": last_exam_date,
            "exam_name": exam_name,
            "target_score": target_score,
            "total_score": total_score,
            "gap": gap,
            "gap_change": gap_change,
        }

    def _upsert_row(self, conn, row: Dict) -> Optional[Tuple[str, str, Optional[str], Optional[int], int]]:
        """
        Returns a change tuple ``(kind, student_name, exam_name, old_gap, new_gap)``
        if the row was inserted or updated, otherwise ``None``.

        ``kind`` is either ``"inserted"`` or ``"updated"``.
        """
        student_id = row["student_id"]
        student_name = row.get("student_name") or ""
        last_exam_date = row.get("last_exam_date")
        exam_name = row.get("exam_name")
        target_score = row.get("target_score")
        total_score = row.get("total_score")
        new_gap = int(row.get("gap") or 0)

        existing = self._select_existing(conn, student_id)
        if existing is None:
            # first insert
            conn.execute(
                """
                INSERT INTO distance (student_id, student_name, last_exam_date, exam_name,
                                      target_score, total_score, gap, gap_change)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (student_id, student_name, last_exam_date, exam_name, target_score, total_score, new_gap),
            )
            return ("inserted", student_name, exam_name, None, new_gap)

        # compare; update if any change (gap_change only when gap changed)
        old_gap = int(existing.get("gap") or 0)
        changed = (
            student_name != existing["student_name"]
            or last_exam_date != existing["last_exam_date"]
            or exam_name != existing["exam_name"]
            or target_score != existing["target_score"]
            or total_score != existing["total_score"]
            or new_gap != old_gap
        )
        if not changed:
            return None

        gap_change = None
        if new_gap != old_gap:
            gap_change = new_gap - old_gap

        conn.execute(
            """
            UPDATE distance
               SET student_name=?, last_exam_date=?, exam_name=?, target_score=?, total_score=?, gap=?, gap_change=?
             WHERE student_id=?
            """,
            (student_name, last_exam_date, exam_name, target_score, total_score, new_gap, gap_change, student_id),
        )
        return ("updated", student_name, exam_name, old_gap, new_gap)

    async def sync_and_collect(self, session, course_id: int) -> Dict:
        """
        Pulls API, upserts DB, collects changes.
        """
        self.ensure_schema(course_id)
        data = await session.api_get_distance_details(course_id)
        inserted = 0
        updated = 0
        changes: List[Tuple[str, str, Optional[str], Optional[int], int, str]] = []
        # (kind, student_name, exam_name, old_gap, new_gap, student_id)

        with self._conn(course_id) as conn:
            for row in data:
                # Normalize fields (API already provides Hebrew text)
                norm = {
                    "student_id": row["student_id"],
                    "student_name": row.get("student_name", ""),
                    "last_exam_date": row.get("last_exam_date"),  # DD-MM-YYYY
                    "exam_name": row.get("exam_name"),
                    "target_score": row.get("target_score"),
                    "total_score": row.get("total_score"),
                    "gap": row.get("gap") or 0,
                }
                ch = self._upsert_row(conn, norm)
                if ch:
                    kind, sname, ename, old_gap, new_gap = ch
                    if kind == "inserted":
                        inserted += 1
                    else:
                        updated += 1
                    changes.append((kind, sname, ename, old_gap, new_gap, norm["student_id"]))
            conn.commit()

        return {
            "inserted": inserted,
            "updated": updated,
            "changes": changes,  # list of tuples
        }
