from __future__ import annotations

import atexit
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response

from app.config import CONFIG
from automation.browser_async import AsyncKidumSession


app = FastAPI()
_session: Optional[AsyncKidumSession] = None


# CORS for your local frontend (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CONFIG.cors_origins or ["http://127.0.0.1:8765", "http://localhost:8765"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# ---------- optional: a tiny index with a form you can use ----------
@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(
        """
<!doctype html>
<html dir="rtl" lang="he">
  <head><meta charset="utf-8"><title>Kidum Automation</title></head>
  <body>
    <h2>Login</h2>
    <form method="post" action="/login">
      <label>שם משתמש: <input type="text" name="username" required></label><br>
      <label>סיסמה: <input type="password" name="password" required></label><br>
      <button type="submit">התחברות</button>
    </form>
    <p><a href="/status">בדיקת סטטוס</a> | <a href="/courses?names_only=true">קורסים (שמות)</a></p>
  </body>
</html>
        """
    )


# stop the 404 noise in logs
@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.on_event("shutdown")
async def _shutdown():
    s = _get_session(False)
    if s:
        try:
            await s.close()
        except Exception:
            # Ignore close errors during shutdown
            pass


@atexit.register
def _atexit_close():
    # Best-effort close when process exits
    import asyncio
    s = _get_session(False)
    if s:
        try:
            asyncio.get_event_loop().run_until_complete(s.close())
        except Exception:
            pass


# ---------- LOGIN that accepts JSON *and* form ----------
@app.post("/login")
async def login(
    request: Request,
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
):
    """
    Accepts either:
      - JSON: {"username": "...", "password": "..."}
      - Form: application/x-www-form-urlencoded (username=...&password=...)
    Logs in via Playwright, then extracts JWT + teacher_id from SPA storage.
    """
    # If JSON, merge it in
    if (username is None or password is None) and request.headers.get("content-type", "").startswith("application/json"):
        try:
            body = await request.json()
        except Exception:
            body = {}
        username = body.get("username", username)
        password = body.get("password", password)

    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing username/password.")

    s = _get_session(True)
    ok = await s.login(username, password)
    if not ok:
        raise HTTPException(status_code=401, detail="Login failed.")

    return {
        "ok": True,
        "display_name": s.get_logged_in_display_name(),
        "teacher_id": s.get_teacher_id(),  # from JWT sub
    }


@app.post("/logout")
async def logout():
    global _session
    s = _get_session(False)
    if s:
        try:
            await s.close()
        except Exception:
            pass
    _session = None
    return {"ok": True}


@app.get("/courses")
async def courses(names_only: bool = False):
    """
    Preferred: call backend API with JWT (no CORS).
    Fallback: scrape the UI react-select if API path fails.
    """
    s = await _ensure_logged_in()

    # Try backend API first
    data: List[Dict] = []
    try:
        data = await s.api_get_courses()
    except Exception:
        # fail quietly and try UI fallback
        pass

    if data:
        if names_only:
            return {"ok": True, "data": [c.get("name", "") for c in data if c.get("name")]}
        return {"ok": True, "data": data}

    # Fallback to UI scraping
    labels = await s.list_classes()
    if names_only:
        return {"ok": True, "data": labels}

    # When scraping, we only have labels — adapt to a uniform shape
    return {"ok": True, "data": [{"name": lbl} for lbl in labels]}


@app.get("/status")
async def status():
    s = _get_session(False)
    return {
        "ok": True,
        "logged_in": bool(s),
        "display_name": s.get_logged_in_display_name() if s else None,
        "teacher_id": s.get_teacher_id() if s else None,
    }
