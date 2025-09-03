# app/webapp.py
from __future__ import annotations

import atexit
from typing import Optional, List, Dict
from pathlib import Path
import subprocess


from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel

from app.config import CONFIG
from automation.api_client import KidumApiSession

from app.services.orchestrator import SyncOrchestrator
from app.services.paths import distance_db_path
from app.db.storage import CourseStore

import sqlite3, html
app = FastAPI()
SYNC = SyncOrchestrator(Path(CONFIG.data_root))

# Frontend root directory
BASE_DIR = Path(__file__).resolve().parents[1]
DIST_DIR = BASE_DIR / "frontend" / "dist"


def _ensure_frontend_build() -> None:
    """Build the frontend if the compiled assets are missing.

    The development `index.html` loads TypeScript modules directly from the
    ``/src`` folder.  Browsers treat those files as plain text and refuse to
    execute them, resulting in ``Failed to load module script`` errors.  In
    production we need the bundled files from ``frontend/dist`` instead.  If
    that directory is absent we invoke ``npm run build`` so that subsequent
    requests serve JavaScript with the correct MIME type.
    """

    index_file = DIST_DIR / "index.html"
    if index_file.exists():
        return
    try:
        subprocess.run(
            ["npm", "run", "build"],
            cwd=BASE_DIR / "frontend",
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        # If building fails we fall back to the uncompiled sources.  The
        # caller can still handle the resulting error, but we avoid raising
        # during import which would break tests.
        pass
app.mount(
    "/assets",
    StaticFiles(directory=DIST_DIR / "assets", check_dir=False),
    name="assets",
)
app.mount(
    "/src",
    StaticFiles(directory=BASE_DIR / "frontend" / "src", check_dir=False),
    name="src",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CONFIG.cors_origins or ["http://127.0.0.1:8765", "http://localhost:8765"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single automation session
_session: Optional[KidumApiSession] = None

def _get_session(create: bool = False) -> Optional[KidumApiSession]:
    global _session
    if _session is None and create:
        _session = KidumApiSession()
    return _session

async def _ensure_logged_in() -> KidumApiSession:
    s = _get_session(False)
    if not s:
        raise HTTPException(status_code=401, detail="Not logged in.")
    return s

class LoginBody(BaseModel):
    username: str
    password: str


class PatchMessageBody(BaseModel):
    content_html: str
    content_json: Dict
    editor_version: str | None = None

@app.on_event("shutdown")
async def _shutdown():
    s = _get_session(False)
    if s:
        try:
            await s.close()
        except Exception:
            pass

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
async def index():
    _ensure_frontend_build()
    index_path = DIST_DIR / "index.html"
    if not index_path.exists():
        index_path = BASE_DIR / "frontend" / "index.html"
    return FileResponse(index_path)

# ---------- API ----------
@app.post("/login")
async def login(body: LoginBody):
    """Log in to a single shared automation session.

    The previous implementation would create the session object before
    verifying the credentials.  If authentication failed, the partially
    initialised session stayed attached to the global ``_session`` variable.
    Subsequent calls to ``/status`` would therefore report
    ``logged_in=True`` even though no valid session existed, causing the
    frontend to redirect straight to the messages page.

    The fix is to only attach the session to the global reference after a
    successful login.  If authentication fails we close the temporary session
    and raise an error so ``/status`` continues to report
    ``logged_in=False``.  A regression test exercises this path to prevent
    future regressions.
    """

    global _session

    # Always start with a fresh session instance. Only persist it globally
    # once the credentials have been verified.
    if _session:
        await _session.close()
        _session = None

    tmp = KidumApiSession()
    ok = False
    try:
        ok = await tmp.login(body.username, body.password)
    except Exception:
        ok = False

    if not ok:
        await tmp.close()
        raise HTTPException(status_code=401, detail="Login failed.")

    _session = tmp
    return {
        "ok": True,
        "display_name": _session.get_logged_in_display_name(),
        "teacher_id": _session.get_teacher_id(),
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

    normalized: List[Dict] = []
    raw = await s.api_get_courses()
    for row in (raw or []):
        cid = row.get("course_id") or row.get("id") or (row.get("courses") or {}).get("id")
        name = row.get("name") or (row.get("courses") or {}).get("name")
        if cid and name:
            try:
                cid = int(cid)
            except Exception:
                pass
            normalized.append({"id": cid, "name": name})

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


@app.get("/status")
async def status():
    s = _get_session(False)
    logged_in = bool(s and s.get_logged_in_display_name())
    return {
        "ok": True,
        "logged_in": logged_in,
        "display_name": s.get_logged_in_display_name() if logged_in else None,
        "teacher_id": s.get_teacher_id() if logged_in else None,
        "selected_id": s.get_selected_course_id() if (logged_in and hasattr(s, "get_selected_course_id")) else None,
    }

# Persist chosen course
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


@app.get("/messages")
async def get_messages(
    course_id: int | None = None,
    type: str = "all",
    search: str | None = None,
    page: int = 1,
    limit: int = 30,
):
    s = await _ensure_logged_in()
    if course_id is None:
        if hasattr(s, "get_selected_course_id") and s.get_selected_course_id():
            course_id = s.get_selected_course_id()
        else:
            raise HTTPException(status_code=400, detail="course_id required")
    res = SYNC.list_messages(
        course_id,
        None if type == "all" else type,
        search=search,
        page=page,
        limit=limit,
    )
    return {
        "ok": True,
        "data": res["rows"],
        "page": page,
        "limit": limit,
        "total": res["total"],
        "types_present": res["types_present"],
    }


@app.get("/message_types")
async def get_message_types(course_id: int):
    await _ensure_logged_in()
    types = SYNC.list_message_types(course_id)
    return {"ok": True, "types": types}


@app.patch("/messages/{msg_id}")
async def patch_message(msg_id: int, body: PatchMessageBody):
    s = await _ensure_logged_in()
    if not hasattr(s, "get_selected_course_id") or not s.get_selected_course_id():
        raise HTTPException(status_code=400, detail="No course selected")
    course_id = s.get_selected_course_id()

    # Sanitize HTML
    import bleach
    from bleach.css_sanitizer import CSSSanitizer

    allowed_tags = [
        "p",
        "h1",
        "h2",
        "h3",
        "strong",
        "em",
        "b",
        "i",
        "u",
        "a",
        "ul",
        "ol",
        "li",
        "blockquote",
        "span",
        "br",
    ]
    allowed_attrs = {"a": ["href"], "span": ["style"], "p": ["style"], "h1": ["style"], "h2": ["style"], "h3": ["style"]}
    clean_html = bleach.clean(
        body.content_html,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True,
        css_sanitizer=CSSSanitizer(),
    )

    try:
        row = SYNC.update_message(
            course_id,
            msg_id,
            content_html=clean_html,
            content_json=body.content_json,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"ok": True, "data": row}


@app.get("/messages/{msg_id}/history")
async def message_history(msg_id: int):
    await _ensure_logged_in()
    # History tracking not yet implemented; return empty list for API compatibility
    return {"ok": True, "history": []}


@app.get("/debug/distance", response_class=HTMLResponse)
async def debug_distance(
    course_id: int | None = Query(default=None),
    refresh: bool = Query(default=False),
    limit: int = Query(default=500),
):
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
        """SELECT student_id, student_name, last_exam_date, exam_name,
                  target_score, total_score, gap, gap_change
             FROM distance
            ORDER BY student_name COLLATE NOCASE
            LIMIT ?""",
        (int(limit),)
    ).fetchall()
    con.close()

    # Render simple HTML table
    def esc(x): return html.escape("" if x is None else str(x))
    trs = "\n".join(
        f"<tr><td>{esc(r[0])}</td><td>{esc(r[1])}</td><td>{esc(r[2])}</td>"
        f"<td>{esc(r[3])}</td><td>{esc(r[4])}</td><td>{esc(r[5])}</td>"
        f"<td>{esc(r[6])}</td><td>{esc(r[7])}</td></tr>"
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
        <th>student_id</th><th>student_name</th><th>last_exam_date</th>
        <th>exam_name</th><th>target_score</th><th>total_score</th>
        <th>gap</th><th>gap_change</th>
      </tr></thead>
      <tbody>
        {trs or '<tr><td colspan="8"><i>אין נתונים</i></td></tr>'}
      </tbody>
    </table>
    </body></html>
    """
    return HTMLResponse(html_doc)


# --- Debug: messages table ---

@app.get("/debug/messages")
async def debug_messages(course_id: int):
    try:
        rows = SYNC.list_messages(course_id)
        return {"ok": True, "count": len(rows), "data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

