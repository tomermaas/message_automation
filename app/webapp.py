# app/webapp.py
from __future__ import annotations

import atexit
from typing import Optional, List, Dict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.config import CONFIG
from automation.browser_async import AsyncKidumSession
from app.services.sync import SyncOrchestrator

from fastapi import Query
import sqlite3
from app.db.storage import CourseStore
app = FastAPI()

# Template engine (ui/web_templates)
BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "ui" / "web_templates"))

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CONFIG.cors_origins or ["http://127.0.0.1:8765", "http://localhost:8765"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single automation session
_session: Optional[AsyncKidumSession] = None

def _get_session(create: bool = False) -> Optional[AsyncKidumSession]:
    global _session
    if _session is None and create:
        _session = AsyncKidumSession()
    return _session

async def _ensure_logged_in() -> AsyncKidumSession:
    s = _get_session(False)
    if not s:
        raise HTTPException(status_code=401, detail="Not logged in.")
    return s

class LoginBody(BaseModel):
    username: str
    password: str

@app.on_event("shutdown")
async def _shutdown():
    s = _get_session(False)
    if s:
        await s.close()

@atexit.register
def _atexit_close():
    import asyncio
    s = _get_session(False)
    if s:
        try:
            asyncio.get_event_loop().run_until_complete(s.close())
        except Exception:
            pass

SYNC = SyncOrchestrator(Path(CONFIG.data_root))

# ---------- UI ----------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    s = _get_session(False)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "logged_in": bool(s),
            "display_name": s.get_logged_in_display_name() if s else None,
            "teacher_id": s.get_teacher_id() if s else None,
            "selected_id": s.get_selected_course_id() if (s and hasattr(s, "get_selected_course_id")) else None,
        },
    )

# ---------- API ----------
@app.post("/login")
async def login(body: LoginBody):
    s = _get_session(True)
    ok = await s.login(body.username, body.password)
    if not ok:
        raise HTTPException(status_code=401, detail="Login failed.")
    return {
        "ok": True,
        "display_name": s.get_logged_in_display_name(),
        "teacher_id": s.get_teacher_id(),
    }

@app.post("/logout")
async def logout():
    global _session
    s = _get_session(False)
    if s:
        await s.close()
    _session = None
    return {"ok": True}

@app.get("/courses")
async def courses(names_only: bool = False):
    s = await _ensure_logged_in()

    data: List[Dict] = []
    try:
        data = await s.api_get_courses()
    except Exception:
        pass

    if data:
        if names_only:
            return {"ok": True, "data": [c.get("name", "") for c in data if c.get("name")], "selected_id": s.get_selected_course_id() if hasattr(s, "get_selected_course_id") else None}
        return {"ok": True, "data": data, "selected_id": s.get_selected_course_id() if hasattr(s, "get_selected_course_id") else None}

    labels = await s.list_classes()
    if names_only:
        return {"ok": True, "data": labels, "selected_id": s.get_selected_course_id() if hasattr(s, "get_selected_course_id") else None}
    return {"ok": True, "data": [{"name": lbl} for lbl in labels], "selected_id": s.get_selected_course_id() if hasattr(s, "get_selected_course_id") else None}

@app.get("/status")
async def status():
    s = _get_session(False)
    return {
        "ok": True,
        "logged_in": bool(s),
        "display_name": s.get_logged_in_display_name() if s else None,
        "teacher_id": s.get_teacher_id() if s else None,
        "selected_id": s.get_selected_course_id() if (s and hasattr(s, "get_selected_course_id")) else None,
    }

# Persist chosen course (ensure these helpers exist on AsyncKidumSession)
class SelectCourseBody(BaseModel):
    course_id: int

@app.post("/select_course")
async def select_course(body: SelectCourseBody):
    s = await _ensure_logged_in()
    if not hasattr(s, "set_selected_course_id"):
        raise HTTPException(status_code=500, detail="Server missing selection support.")
    s.set_selected_course_id(body.course_id)

    # Run the sync immediately
    orch = SyncOrchestrator(Path(CONFIG.data_root))
    summary = await orch.run(s, body.course_id)

    return {"ok": True, "selected_id": s.get_selected_course_id(), "sync": summary}

from fastapi import Query

@app.get("/debug/distance")
async def debug_distance(course_id: int | None = Query(None)):
    s = await _ensure_logged_in()
    # Try query param, else use the current selection
    cid = course_id or (s.get_selected_course_id() if hasattr(s, "get_selected_course_id") else None)
    if not cid:
        raise HTTPException(status_code=400, detail="Provide ?course_id=... or select a course first.")

    # read the SQLite
    import sqlite3
    from app.db.storage import CourseStore
    store = CourseStore(Path(CONFIG.data_root), int(cid), s.get_teacher_id())
    db = store.db_path("distance.sqlite")
    if not db.exists():
        return {"ok": True, "rows": []}

    conn = sqlite3.connect(str(db))
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT student_id, student_name_he, last_exam_date, exam_name_he, target_score, total_score
            FROM distances
            WHERE course_id=?
            ORDER BY student_name_he
        """, (int(cid),))
        rows = [
            {
                "student_id": r[0],
                "student_name_he": r[1],
                "last_exam_date": r[2],
                "exam_name_he": r[3],
                "target_score": r[4],
                "total_score": r[5],
            }
            for r in cur.fetchall()
        ]
        return {"ok": True, "rows": rows, "course_id": int(cid)}
    finally:
        conn.close()
