# app/db/handlers/distance_sqlite.py
from __future__ import annotations
import sqlite3, os
from pathlib import Path
from typing import Iterable, Dict, Any, Tuple, List

DDL = """
CREATE TABLE IF NOT EXISTS distance (
  student_id      TEXT PRIMARY KEY,
  student_name_he TEXT,
  last_exam_date  TEXT,      -- kept 'DD-MM-YYYY' as-is
  exam_name_he    TEXT,
  target_score    TEXT,
  total_score     TEXT,
  gap             INTEGER,
  gap_change      INTEGER,   -- NULL unless gap changed this sync
  updated_at      TEXT
);
"""

class DistanceSQLite:
    def __init__(self, db_path: Path):
        os.makedirs(db_path.parent, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(DDL)
        self.conn.commit()

    def close(self):
        try: self.conn.close()
        except Exception: pass

    def upsert_many(self, rows: Iterable[Dict[str, Any]]) -> Tuple[int, int, List[str]]:
        """
        Returns (inserted, updated, changed_ids) where changed_ids includes inserts
        and rows whose gap changed.
        """
        ins = upd = 0
        changed_ids: List[str] = []
        cur = self.conn.cursor()

        for r in rows:
            sid = r["student_id"]
            gap = int(r.get("gap") or 0)

            cur.execute("SELECT gap FROM distance WHERE student_id=?", (sid,))
            row = cur.fetchone()

            if row is None:
                cur.execute(
                    """INSERT INTO distance
                       (student_id, student_name_he, last_exam_date, exam_name_he,
                        target_score, total_score, gap, gap_change, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, NULL, datetime('now'))""",
                    (
                        sid,
                        r.get("student_name_he") or r.get("student_name") or "",
                        r.get("last_exam_date") or "",
                        r.get("exam_name_he") or r.get("exam_name") or "",
                        r.get("target_score") or "",
                        r.get("total_score") or "",
                        gap,
                    ),
                )
                ins += 1
                changed_ids.append(sid)  # treat first insert as "changed"
            else:
                old_gap = int(row[0] if row[0] is not None else 0)
                gap_change = None
                gap_diff = gap - old_gap
                if old_gap != gap:
                    gap_change = gap_diff
                    changed_ids.append(sid)

                cur.execute(
                    """UPDATE distance
                       SET student_name_he=?,
                           last_exam_date=?,
                           exam_name_he=?,
                           target_score=?,
                           total_score=?,
                           gap=?,
                           gap_change=?,
                           updated_at=datetime('now')
                       WHERE student_id=?""",
                    (
                        r.get("student_name_he") or r.get("student_name") or "",
                        r.get("last_exam_date") or "",
                        r.get("exam_name_he") or r.get("exam_name") or "",
                        r.get("target_score") or "",
                        r.get("total_score") or "",
                        gap,
                        gap_change,   # NULL if no gap change
                        sid,
                    ),
                )
                upd += 1

        self.conn.commit()
        return ins, upd, changed_ids
