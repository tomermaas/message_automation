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

from app.services.orchestrator import SyncOrchestrator
from app.services.paths import course_dir

from fastapi import Query
from app.services.paths import distance_db_path
import sqlite3, html



from fastapi import Query
import sqlite3
from app.db.storage import CourseStore
app = FastAPI()
SYNC = SyncOrchestrator(Path(CONFIG.data_root))

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

    # Try backend API first
    normalized: List[Dict] = []
    try:
        raw = await s.api_get_courses()  # returns the LMS payload you showed
        # Normalize to [{id, name}]
        for row in (raw or []):
            cid = row.get("course_id") or row.get("id") or (row.get("courses") or {}).get("id")
            name = row.get("name") or (row.get("courses") or {}).get("name")
            if cid and name:
                try:
                    cid = int(cid)
                except Exception:
                    pass
                normalized.append({"id": cid, "name": name})
    except Exception:
        # fall through to UI scraping
        normalized = []

    if normalized:
        if names_only:
            return {
                "ok": True,
                "data": [c["name"] for c in normalized],
                "selected_id": s.get_selected_course_id() if hasattr(s, "get_selected_course_id") else None,
            }
        return {
            "ok": True,
            "data": normalized,
            "selected_id": s.get_selected_course_id() if hasattr(s, "get_selected_course_id") else None,
        }

    # Fallback (UI scrape only returns labels; no IDs available)
    labels = await s.list_classes()
    if names_only:
        return {
            "ok": True,
            "data": labels,
            "selected_id": s.get_selected_course_id() if hasattr(s, "get_selected_course_id") else None,
        }
    return {
        "ok": True,
        "data": [{"id": None, "name": lbl} for lbl in labels],
        "selected_id": s.get_selected_course_id() if hasattr(s, "get_selected_course_id") else None,
    }


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

class SelectCourseBody(BaseModel):
    course_id: int

@app.post("/select_course")
async def select_course(body: SelectCourseBody):
    s = await _ensure_logged_in()
    if not hasattr(s, "set_selected_course_id"):
        raise HTTPException(status_code=500, detail="Server missing selection support.")
    s.set_selected_course_id(body.course_id)

    # RUN SYNC NOW so messages are generated
    summary = await SYNC.sync_all(s, body.course_id)

    return {"ok": True, "selected_id": s.get_selected_course_id(), "summary": summary}


from fastapi import Query

@app.get("/debug/distance", response_class=HTMLResponse)
async def debug_distance(request: Request,
                         course_id: int | None = Query(default=None),
                         refresh: bool = Query(default=False),
                         limit: int = Query(default=500)):
    s = _get_session(False)
    # Resolve course id: explicit param > selected in session
    if course_id is None:
        if s and s.get_selected_course_id():
            course_id = s.get_selected_course_id()
        else:
            return HTMLResponse("No course selected. Supply ?course_id=... or select a course in the UI.", status_code=400)

    # Optionally re-sync
    if refresh and s:
        try:
            from app.services.orchestrator import create_orchestrator
            _sync = create_orchestrator()
            await _sync.run(s, int(course_id))
        except Exception as e:
            return HTMLResponse(f"Sync failed: {html.escape(str(e))}", status_code=500)

    dbp = distance_db_path(int(course_id))
    if not dbp.exists():
        return HTMLResponse(f"DB missing for course {course_id} at {dbp}. Select the course first.", status_code=404)

    con = sqlite3.connect(dbp)
    cur = con.cursor()
    rows = cur.execute(
        """SELECT student_id, student_name_he, last_exam_date, exam_name_he,
                  target_score, total_score, gap, gap_change, updated_at
             FROM distance
            ORDER BY student_name_he COLLATE NOCASE
            LIMIT ?""",
        (int(limit),)
    ).fetchall()
    con.close()

    # Render simple HTML table
    def esc(x): return html.escape("" if x is None else str(x))
    trs = "\n".join(
        f"<tr><td>{esc(r[0])}</td><td>{esc(r[1])}</td><td>{esc(r[2])}</td>"
        f"<td>{esc(r[3])}</td><td>{esc(r[4])}</td><td>{esc(r[5])}</td>"
        f"<td>{esc(r[6])}</td><td>{esc(r[7])}</td><td>{esc(r[8])}</td></tr>"
        for r in rows
    )
    html_doc = f"""
    <html dir="rtl" lang="he"><head><meta charset="utf-8">
    <title>Debug Distance</title>
    <style>table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:.3rem .5rem}}</style>
    </head><body>
    <h2>Distance DB — Course {esc(course_id)}</h2>
    <p><a href="/debug/distance?course_id={esc(course_id)}&refresh=1">רענן / סנכרן כעת</a></p>
    <table>
      <thead><tr>
        <th>student_id</th><th>student_name_he</th><th>last_exam_date</th>
        <th>exam_name_he</th><th>target_score</th><th>total_score</th>
        <th>gap</th><th>gap_change</th><th>updated_at</th>
      </tr></thead>
      <tbody>
        {trs or '<tr><td colspan="9"><i>אין נתונים</i></td></tr>'}
      </tbody>
    </table>
    </body></html>
    """
    return HTMLResponse(html_doc)
# --- Debug: messages table ---
from app.db.storage import CourseStore
from pathlib import Path

@app.get("/debug/messages")
async def debug_messages(course_id: int):
    try:
        rows = SYNC.list_messages(course_id)
        return {"ok": True, "count": len(rows), "data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

