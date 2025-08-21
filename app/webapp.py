from __future__ import annotations

import atexit
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

from app.config import CONFIG
from automation.browser_async import AsyncKidumSession


app = FastAPI()
_session: Optional[AsyncKidumSession] = None


# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=CONFIG.cors_origins or ["http://127.0.0.1:8765", "http://localhost:8765"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Session helpers ----------
def _get_session(create: bool = False, headless: Optional[bool] = None) -> Optional[AsyncKidumSession]:
    """
    Returns the current session or creates one (headless respected on creation only).
    """
    global _session
    if _session is None and create:
        _session = AsyncKidumSession(headless=headless)
    return _session


async def _new_session(headless: Optional[bool]) -> AsyncKidumSession:
    """
    Close any existing session and create a new one (used to switch headless on login).
    """
    global _session
    if _session:
        try:
            await _session.close()
        except Exception:
            pass
    _session = AsyncKidumSession(headless=headless)
    return _session


async def _ensure_logged_in() -> AsyncKidumSession:
    s = _get_session(False)
    if not s:
        raise HTTPException(status_code=401, detail="Not logged in.")
    return s


# ---------- Models ----------
class LoginBody(BaseModel):
    username: str
    password: str
    # When true, we want a visible browser => headless=False
    show_browser: bool | None = None


# ---------- Lifecycle ----------
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


# ---------- Routes ----------
@app.get("/", response_class=HTMLResponse)
async def index():
    # Simple, clean RTL UI with a real <select> that fills after login
    return HTMLResponse(
        """
<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Kidum Automation</title>
<style>
  :root {
    --bg:#0b1020;
    --panel:#111937;
    --muted:#9aa4b2;
    --text:#e8edf4;
    --accent:#f70035;
    --accent-2:#33c2ff;
    --ok:#16a34a;
    --warn:#eab308;
    --err:#ef4444;
    --border:#1f2a4b;
  }
  * { box-sizing: border-box; font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", "Noto Sans", "Helvetica Neue", Arial, "Apple Color Emoji","Segoe UI Emoji"; }
  body { margin:0; background: linear-gradient(180deg, #0b1020 0%, #0e1430 60%, #0b1020 100%); color:var(--text); }
  .wrap { max-width: 900px; margin: 40px auto; padding: 0 16px; }
  .card { background: var(--panel); border: 1px solid var(--border); border-radius: 16px; padding: 20px; box-shadow: 0 10px 30px rgba(0,0,0,.25); }
  h1 { font-size: 24px; margin: 0 0 16px; }
  .row { display: grid; gap: 12px; grid-template-columns: 1fr 1fr; }
  .row-3 { display: grid; gap: 12px; grid-template-columns: 1fr 1fr 1fr; }
  label { font-size: 14px; color: var(--muted); }
  input[type="text"], input[type="password"], select {
    width: 100%; padding: 10px 12px; border-radius: 10px;
    border: 1px solid var(--border); background: #0c1430; color: var(--text);
    outline: none;
  }
  input[type="checkbox"] { transform: scale(1.2); }
  .btn {
    appearance: none; border: none; border-radius: 12px; padding: 10px 14px; cursor: pointer; font-weight: 600;
    color: white; background: linear-gradient(90deg, var(--accent) 0%, #ff5a83 100%);
    box-shadow: 0 4px 14px rgba(247,0,53,.35);
  }
  .btn.secondary {
    background: linear-gradient(90deg, var(--accent-2) 0%, #5fe0ff 100%);
    box-shadow: 0 4px 14px rgba(51,194,255,.3);
  }
  .btn.ghost { background: transparent; border: 1px solid var(--border); color: var(--text); }
  .muted { color: var(--muted); }
  .split { display:flex; gap:16px; flex-wrap: wrap; }
  .pill { border: 1px solid var(--border); border-radius: 999px; padding: 6px 10px; font-size: 13px; color: var(--muted); }
  .kv { display:flex; gap:6px; align-items:center; }
  .status-ok { color: var(--ok); font-weight:600; }
  .status-err { color: var(--err); font-weight:600; }
  .status-warn { color: var(--warn); font-weight:600; }
  .mt16 { margin-top: 16px; }
  .mt8 { margin-top: 8px; }
  .mb8 { margin-bottom: 8px; }
  .grid { display:grid; gap: 16px; }
  .hidden { display:none; }
  small { color: var(--muted); }
</style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>🔐 כניסה למערכת אוטומציה</h1>
      <div class="grid">
        <div class="row">
          <div>
            <label>שם משתמש</label>
            <input id="username" type="text" autocomplete="username" />
          </div>
          <div>
            <label>סיסמה</label>
            <input id="password" type="password" autocomplete="current-password" />
          </div>
        </div>
        <div class="split">
          <label class="kv"><input id="showBrowser" type="checkbox" />
            <span class="muted">הצג חלון דפדפן אוטומציה (לא Headless)</span></label>
          <button id="btnLogin" class="btn">התחברות</button>
          <button id="btnLogout" class="btn ghost">התנתקות</button>
          <span id="loginMsg" class="muted"></span>
        </div>
      </div>

      <hr class="mt16" style="border: none; border-top:1px solid var(--border)" />

      <div class="grid mt16">
        <div class="row-3">
          <div class="pill">סטטוס: <span id="status" class="status-warn">לא מחובר</span></div>
          <div class="pill">שם מוצג: <span id="displayName">—</span></div>
          <div class="pill">Teacher ID: <span id="teacherId">—</span></div>
        </div>
      </div>

      <div class="grid mt16">
        <div class="row">
          <div>
            <label>בחר קורס</label>
            <select id="courseSelect">
              <option value="">— אין נתונים —</option>
            </select>
            <div class="mt8">
              <button id="btnLoadCourses" class="btn secondary">רענן רשימת קורסים</button>
              <small id="coursesMsg" class="muted"></small>
            </div>
          </div>
          <div>
            <label>מידע</label>
            <div class="muted" style="line-height:1.6">
              • לאחר התחברות, רשימת הקורסים נטענת אוטומטית מה-API.<br />
              • אם ה-API ייכשל, נעשה ניסיון גיבוי דרך ה-UI (איטי יותר).<br />
              • אפשר להציג דפדפן אמיתי (בטל Headless) ע״י סימון התיבה לפני התחברות.
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>

<script>
async function $get(url) {
  const r = await fetch(url, { credentials: 'include' });
  if (!r.ok) throw new Error(`GET ${url} -> ${r.status}`);
  return r.json();
}
async function $post(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {})
  });
  const text = await r.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch(e){ data = { ok:false, error:text }; }
  if (!r.ok) {
    const msg = (data && data.detail) ? data.detail : (`HTTP ${r.status}`);
    throw new Error(msg);
  }
  return data;
}
function setStatus(s) {
  const el = document.getElementById('status');
  el.classList.remove('status-ok','status-err','status-warn');
  if (s === true) { el.textContent = 'מחובר'; el.classList.add('status-ok'); }
  else if (s === false) { el.textContent = 'לא מחובר'; el.classList.add('status-warn'); }
  else { el.textContent = s; el.classList.add('status-err'); }
}
function setProfile(displayName, teacherId) {
  document.getElementById('displayName').textContent = displayName || '—';
  document.getElementById('teacherId').textContent = teacherId || '—';
}
function fillCourses(names) {
  const sel = document.getElementById('courseSelect');
  sel.innerHTML = '';
  if (!names || names.length === 0) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = '— אין נתונים —';
    sel.appendChild(opt);
    return;
  }
  for (const name of names) {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name;
    sel.appendChild(opt);
  }
}
async function refreshStatusAndMaybeLoad() {
  try {
    const s = await $get('/status');
    setStatus(!!s.logged_in);
    setProfile(s.display_name, s.teacher_id);
    if (s.logged_in) {
      await loadCourses(true);
    } else {
      fillCourses([]);
    }
  } catch (e) {
    setStatus(String(e.message || e));
  }
}
async function loadCourses(auto=false) {
  const msg = document.getElementById('coursesMsg');
  msg.textContent = auto ? 'טוען קורסים...' : 'מרענן קורסים...';
  try {
    const data = await $get('/courses?names_only=true');
    if (data && data.ok) {
      fillCourses(data.data || []);
      msg.textContent = `נמצאו ${data.data?.length ?? 0} קורסים.`;
    } else {
      msg.textContent = 'שגיאה בטעינת קורסים.';
    }
  } catch (e) {
    msg.textContent = 'שגיאה: ' + (e.message || e);
  }
}
async function doLogin() {
  const u = document.getElementById('username').value.trim();
  const p = document.getElementById('password').value;
  const show = document.getElementById('showBrowser').checked;
  const m = document.getElementById('loginMsg');
  m.textContent = 'מתחבר...';
  try {
    const data = await $post('/login', { username: u, password: p, show_browser: show });
    m.textContent = 'התחברות הצליחה.';
    setStatus(true);
    setProfile(data.display_name, data.teacher_id);
    await loadCourses(true);
  } catch (e) {
    setStatus(false);
    m.textContent = 'שגיאה: ' + (e.message || e);
  }
}
async function doLogout() {
  const m = document.getElementById('loginMsg');
  m.textContent = 'מתנתק...';
  try {
    await $post('/logout', {});
    m.textContent = 'התנתקת.';
    setStatus(false);
    setProfile(null, null);
    fillCourses([]);
  } catch (e) {
    m.textContent = 'שגיאה: ' + (e.message || e);
  }
}
document.getElementById('btnLogin').addEventListener('click', doLogin);
document.getElementById('btnLogout').addEventListener('click', doLogout);
document.getElementById('btnLoadCourses').addEventListener('click', () => loadCourses(false));
refreshStatusAndMaybeLoad();
</script>
</body>
</html>
        """
    )


@app.get("/favicon.ico")
async def favicon():
    # quiet the logs
    return Response(status_code=204)


@app.post("/login")
async def login(body: LoginBody):
    """
    Logs in via Playwright, extracts JWT + teacher_id from SPA storage.
    show_browser=True => headless=False
    """
    # Decide headless based on the checkbox; default to CONFIG.headless
    headless = CONFIG.headless
    if body.show_browser is not None:
        headless = not body.show_browser

    # Re-create a session with the requested headless mode
    s = await _new_session(headless=headless)

    ok = await s.login(body.username, body.password)
    if not ok:
        # don't keep a half-baked session
        await s.close()
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

    data: List[Dict] = []
    try:
        data = await s.api_get_courses()
    except Exception:
        # Fallback to UI scraping
        pass

    if data:
        if names_only:
            return {"ok": True, "data": [c.get("name", "") for c in data if c.get("name")]}
        return {"ok": True, "data": data}

    # UI fallback:
    labels = await s.list_classes()
    if names_only:
        return {"ok": True, "data": labels}
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
