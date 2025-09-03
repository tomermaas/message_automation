from __future__ import annotations

"""Synchronise distance/score-gap data into PostgreSQL."""

from typing import Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.config import CONFIG
from app.db.postgres_setup import ensure_teacher_schema, get_engine


class DistanceSyncer:
    """Maintains the ``score_gap`` table for a teacher."""

    def __init__(self, teacher_id: str, engine: Engine | None = None):
        self.teacher_id = str(teacher_id)
        self.engine = engine or get_engine(CONFIG.database_url)
        ensure_teacher_schema(self.engine, self.teacher_id)
        self.schema = f"teacher_{self.teacher_id}"

    # ------------------------------------------------------------------
    def _select_existing(
        self, conn, course_id: int, student_id: str
    ) -> Optional[Dict]:
        row = conn.execute(
            text(
                f"""
                SELECT student_name, last_exam_date, exam_name,
                       target_score, total_score, gap, gap_change
                  FROM "{self.schema}".score_gap
                 WHERE course_id=:course_id AND student_id=:student_id
                """
            ),
            {"course_id": course_id, "student_id": student_id},
        ).fetchone()
        if not row:
            return None
        (
            student_name,
            last_exam_date,
            exam_name,
            target_score,
            total_score,
            gap,
            gap_change,
        ) = row
        return {
            "student_name": student_name,
            "last_exam_date": last_exam_date,
            "exam_name": exam_name,
            "target_score": target_score,
            "total_score": total_score,
            "gap": gap,
            "gap_change": gap_change,
        }

    def _upsert_row(
        self, conn, course_id: int, row: Dict
    ) -> Optional[Tuple[str, str, Optional[str], Optional[int], int]]:
        student_id = row["student_id"]
        student_name = row.get("student_name") or ""
        last_exam_date = row.get("last_exam_date")
        exam_name = row.get("exam_name")
        target_score = row.get("target_score")
        total_score = row.get("total_score")
        new_gap = int(row.get("gap") or 0)

        existing = self._select_existing(conn, course_id, student_id)
        if existing is None:
            conn.execute(
                text(
                    f"""
                    INSERT INTO "{self.schema}".score_gap (
                        course_id, student_id, student_name, last_exam_date,
                        exam_name, target_score, total_score, gap, gap_change
                    ) VALUES (
                        :course_id, :student_id, :student_name, :last_exam_date,
                        :exam_name, :target_score, :total_score, :gap, NULL
                    )
                    """
                ),
                {
                    "course_id": course_id,
                    "student_id": student_id,
                    "student_name": student_name,
                    "last_exam_date": last_exam_date,
                    "exam_name": exam_name,
                    "target_score": target_score,
                    "total_score": total_score,
                    "gap": new_gap,
                },
            )
            return ("inserted", student_name, exam_name, None, new_gap)

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
            text(
                f"""
                UPDATE "{self.schema}".score_gap
                   SET student_name=:student_name,
                       last_exam_date=:last_exam_date,
                       exam_name=:exam_name,
                       target_score=:target_score,
                       total_score=:total_score,
                       gap=:gap,
                       gap_change=:gap_change
                 WHERE course_id=:course_id AND student_id=:student_id
                """
            ),
            {
                "student_name": student_name,
                "last_exam_date": last_exam_date,
                "exam_name": exam_name,
                "target_score": target_score,
                "total_score": total_score,
                "gap": new_gap,
                "gap_change": gap_change,
                "course_id": course_id,
                "student_id": student_id,
            },
        )
        return ("updated", student_name, exam_name, old_gap, new_gap)

    # ------------------------------------------------------------------
    async def sync_and_collect(self, session, course_id: int) -> Dict:
        data = await session.api_get_distance_details(course_id)
        inserted = 0
        updated = 0
        changes: List[Tuple[str, str, Optional[str], Optional[int], int, str]] = []

        with self.engine.begin() as conn:
            for row in data:
                norm = {
                    "student_id": row["student_id"],
                    "student_name": row.get("student_name", ""),
                    "last_exam_date": row.get("last_exam_date"),
                    "exam_name": row.get("exam_name"),
                    "target_score": row.get("target_score"),
                    "total_score": row.get("total_score"),
                    "gap": row.get("gap") or 0,
                }
                ch = self._upsert_row(conn, course_id, norm)
                if ch:
                    kind, sname, ename, old_gap, new_gap = ch
                    if kind == "inserted":
                        inserted += 1
                    else:
                        updated += 1
                    changes.append((kind, sname, ename, old_gap, new_gap, norm["student_id"]))
        return {"inserted": inserted, "updated": updated, "changes": changes}

    # ------------------------------------------------------------------
    def get_student(self, course_id: int, student_id: str) -> Optional[Dict]:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    f"""
                    SELECT student_name, last_exam_date, exam_name, target_score,
                           total_score, gap, gap_change
                      FROM "{self.schema}".score_gap
                     WHERE course_id=:course_id AND student_id=:student_id
                    """
                ),
                {"course_id": course_id, "student_id": student_id},
            ).fetchone()
        if not row:
            return None
        (
            sname,
            last_exam_date,
            exam_name,
            target_score,
            total_score,
            gap,
            gap_change,
        ) = row
        return {
            "student_name": sname,
            "last_exam_date": last_exam_date,
            "exam_name": exam_name,
            "target_score": target_score,
            "total_score": total_score,
            "gap": gap,
                "gap_change": gap_change,
            }

    # ------------------------------------------------------------------
    def list_students(self, course_id: int) -> List[Dict]:
        """Return all score-gap rows for ``course_id``."""

        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT student_id, student_name, last_exam_date, exam_name,
                           target_score, total_score, gap, gap_change
                      FROM "{self.schema}".score_gap
                     WHERE course_id=:course_id
                    """
                ),
                {"course_id": course_id},
            ).fetchall()
        data: List[Dict] = []
        for r in rows:
            (
                sid,
                sname,
                last_exam_date,
                exam_name,
                target_score,
                total_score,
                gap,
                gap_change,
            ) = r
            data.append(
                {
                    "student_id": sid,
                    "student_name": sname,
                    "last_exam_date": last_exam_date,
                    "exam_name": exam_name,
                    "target_score": target_score,
                    "total_score": total_score,
                    "gap": gap,
                    "gap_change": gap_change,
                }
            )
        return data
