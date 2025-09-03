from __future__ import annotations

"""PostgreSQL-backed persistence layer for student messages."""

import json
import time
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.config import CONFIG
from app.db.postgres_setup import ensure_teacher_schema, get_engine


class MessagesStore:
    """Store and retrieve messages in the per-teacher schema."""

    def __init__(self, teacher_id: str, engine: Engine | None = None) -> None:
        self.teacher_id = str(teacher_id)
        self.engine = engine or get_engine(CONFIG.database_url)
        ensure_teacher_schema(self.engine, self.teacher_id)
        self.schema = f"teacher_{self.teacher_id}"

    # ------------------------------------------------------------------
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
        """Insert or update a message row."""

        ts = int(time.time()) if created_at is None else created_at
        meta_json = json.dumps(meta or {}, ensure_ascii=False)
        content_json_str = json.dumps(content_json, ensure_ascii=False)
        stmt = text(
            f"""
            INSERT INTO "{self.schema}".messages (
                course_id, db_type, student_id, student_name,
                created_at, updated_at, content_html, content_json, source, meta
            ) VALUES (
                :course_id, :db_type, :student_id, :student_name,
                :created_at, :updated_at, :content_html, :content_json, :source, :meta
            )
            ON CONFLICT (course_id, db_type, student_id) DO UPDATE SET
                student_name=excluded.student_name,
                updated_at=excluded.updated_at,
                meta=excluded.meta,
                content_html=CASE WHEN "{self.schema}".messages.source='auto'
                                  THEN excluded.content_html ELSE "{self.schema}".messages.content_html END,
                content_json=CASE WHEN "{self.schema}".messages.source='auto'
                                   THEN excluded.content_json ELSE "{self.schema}".messages.content_json END,
                source=CASE WHEN "{self.schema}".messages.source='auto'
                            THEN excluded.source ELSE "{self.schema}".messages.source END
            """
        )
        with self.engine.begin() as conn:
            conn.execute(
                stmt,
                {
                    "course_id": course_id,
                    "db_type": db_type,
                    "student_id": student_id,
                    "student_name": student_name,
                    "created_at": ts,
                    "updated_at": ts,
                    "content_html": content_html,
                    "content_json": content_json_str,
                    "source": source,
                    "meta": meta_json,
                },
            )

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
        offset = (page - 1) * limit
        where = ["course_id = :course_id"]
        params = {"course_id": course_id, "limit": limit, "offset": offset}
        if msg_type:
            where.append("db_type = :db_type")
            params["db_type"] = msg_type
        if search:
            where.append("student_name ILIKE :search")
            params["search"] = f"%{search}%"
        where_sql = " AND ".join(where)
        with self.engine.begin() as conn:
            total = conn.execute(
                text(
                    f'SELECT COUNT(*) FROM "{self.schema}".messages WHERE {where_sql}'
                ),
                params,
            ).scalar()
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, course_id, db_type, student_id, student_name,
                           created_at, updated_at, content_html, content_json,
                           source, meta
                      FROM "{self.schema}".messages
                     WHERE {where_sql}
                  ORDER BY student_name
                     LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            ).fetchall()
        data: List[Dict] = []
        for row in rows:
            (
                mid,
                cid,
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
                    "course_id": cid,
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
        return {"rows": data, "total": total or 0, "types_present": types_present}

    # ------------------------------------------------------------------
    def list_types(self, course_id: int) -> List[str]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    f'SELECT DISTINCT db_type FROM "{self.schema}".messages '
                    'WHERE course_id=:cid ORDER BY db_type'
                ),
                {"cid": course_id},
            ).fetchall()
        return [r[0] for r in rows]

    # ------------------------------------------------------------------
    def update_message(
        self,
        course_id: int,
        msg_id: int,
        *,
        content_html: str,
        content_json: Dict,
        source: str = "manual",
    ) -> Dict:
        now = int(time.time())
        content_json_str = json.dumps(content_json, ensure_ascii=False)
        stmt = text(
            f"""
            UPDATE "{self.schema}".messages
               SET content_html=:content_html,
                   content_json=:content_json,
                   updated_at=:updated_at,
                   source=:source
             WHERE id=:id AND course_id=:course_id
         RETURNING id, course_id, db_type, student_id, student_name,
                   created_at, updated_at, content_html, content_json,
                   source, meta
            """
        )
        with self.engine.begin() as conn:
            row = conn.execute(
                stmt,
                {
                    "content_html": content_html,
                    "content_json": content_json_str,
                    "updated_at": now,
                    "source": source,
                    "id": msg_id,
                    "course_id": course_id,
                },
            ).fetchone()
        if not row:
            raise KeyError(msg_id)
        (
            mid,
            cid,
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
            "course_id": cid,
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
