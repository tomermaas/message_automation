from __future__ import annotations
import os
import json
import base64
import re
from typing import Optional, List, Dict, Any

from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError
import httpx

from app.config import CONFIG

SUCCESS_LABEL_SELECTOR = 'label[for="select-placeholder"]'

# Known react-select control classes seen in your DOM
CONTROL_SEL = "div.css-13cymwt-control, div[class*='__control'], div[class*='control']"
SINGLE_VALUE_SEL = "div.css-1dimb5e-singleValue, div[class*='singleValue']"
INDICATOR_SEL = "div.css-1xc3v61-indicatorContainer, div[class*='indicatorContainer']"
INPUT_SEL = 'input[id^="react-select-"][id$="-input"][role="combobox"]'
MENU_SEL = 'div[id^="react-select-"][id$="-listbox"], div[role="listbox"]'
OPTION_SEL = 'div[id^="react-select-"][id$="-option-"], [role="option"]'


class AsyncKidumSession:
    def __init__(self, headless: Optional[bool] = None):
        self._pw = None
        self._browser = None
        self._page = None
        self._headless = CONFIG.headless if headless is None else headless
        self._display_name: Optional[str] = None
        self._jwt: Optional[str] = None
        self._teacher_id: Optional[str] = None
        self._bound_req_listener = False
        self._selected_course_id: Optional[int] = None

    # ---------- lifecycle ----------
    async def _ensure_started(self):
        if self._browser is not None:
            return
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self._headless,
            args=["--no-sandbox"],
        )
        self._page = await self._browser.new_page()
        self._page.set_default_timeout(15000)
        self._bind_request_listener()

    async def close(self):
        try:
            if self._browser:
                await self._browser.close()
        finally:
            self._browser = None
            if self._pw:
                await self._pw.stop()
                self._pw = None
            self._page = None
            self._jwt = None
            self._teacher_id = None
            self._display_name = None
            self._bound_req_listener = False

    @property
    def page(self):
        return self._page

    def get_logged_in_display_name(self) -> Optional[str]:
        return self._display_name

    def get_teacher_id(self) -> Optional[str]:
        return self._teacher_id
    def set_selected_course_id(self, course_id: Optional[int]) -> None:
        self._selected_course_id = int(course_id) if course_id is not None else None

    def get_selected_course_id(self) -> Optional[int]:
        return self._selected_course_id


    # ---------- debug ----------
    async def _debug_dump(self, tag: str) -> None:
        try:
            os.makedirs("data/sample", exist_ok=True)
            await self.page.screenshot(path=f"data/sample/{tag}.png", full_page=True)
            html = await self.page.content()
            with open(f"data/sample/{tag}.html", "w", encoding="utf-8") as f:
                f.write(html)
        except Exception:
            pass

    # ---------- auth helpers ----------
    def _bind_request_listener(self):
        if not self._page or self._bound_req_listener:
            return

        def _on_request(req):
            try:
                auth = req.headers.get("authorization") or req.headers.get("Authorization")
                if auth and "Bearer " in auth and not self._jwt:
                    token = auth.split("Bearer ", 1)[1].strip()
                    if self._looks_like_jwt(token):
                        self._jwt = token
                        if not self._teacher_id:
                            self._teacher_id = self._decode_jwt_sub(token)
            except Exception:
                pass

        self._page.on("request", _on_request)
        self._bound_req_listener = True

    @staticmethod
    def _looks_like_jwt(s: str) -> bool:
        return bool(re.match(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$", s.strip()))

    @staticmethod
    def _b64url_decode(s: str) -> bytes:
        s += "=" * ((4 - len(s) % 4) % 4)
        return base64.urlsafe_b64decode(s.encode("utf-8"))

    def _decode_jwt_sub(self, jwt: str) -> Optional[str]:
        try:
            parts = jwt.split(".")
            if len(parts) != 3:
                return None
            payload = json.loads(self._b64url_decode(parts[1]).decode("utf-8"))
            return payload.get("sub")
        except Exception:
            return None

    async def _harvest_jwt_from_storage(self) -> None:
        """Scan localStorage/sessionStorage for a JWT (even embedded JSON)."""
        page = self.page
        if not page:
            return

        js = """
(() => {
  const extractToken = (val) => {
    if (!val) return null;
    let s = typeof val === 'string' ? val : JSON.stringify(val);
    // Try explicit Bearer
    let m = s.match(/Bearer\\s+([A-Za-z0-9-_]+\\.[A-Za-z0-9-_]+\\.[A-Za-z0-9-_]+)/);
    if (m) return m[1];
    // Try raw JWT
    m = s.match(/([A-Za-z0-9-_]+\\.[A-Za-z0-9-_]+\\.[A-Za-z0-9-_]+)/);
    if (m) return m[1];
    return null;
  };
  const scan = (store) => {
    if (!store) return null;
    const keys = [];
    for (let i = 0; i < store.length; i++) keys.push(store.key(i));
    for (const k of keys) {
      try {
        const v = store.getItem(k);
        let t = extractToken(v);
        if (t) return t;
        try {
          const o = JSON.parse(v);
          t = extractToken(o);
          if (t) return t;
        } catch (_) {}
      } catch (_) {}
    }
    return null;
  };
  return scan(window.localStorage) || scan(window.sessionStorage) || null;
})()
"""
        try:
            token = await page.evaluate(js)
            if token and self._looks_like_jwt(token):
                self._jwt = token
                if not self._teacher_id:
                    self._teacher_id = self._decode_jwt_sub(token)
        except Exception:
            pass

    def debug_auth_snapshot(self) -> Dict[str, Any]:
        """Safe to return in /debug_auth."""
        preview = None
        if self._jwt:
            preview = self._jwt[:20] + "..." if len(self._jwt) > 20 else self._jwt
        return {
            "have_jwt": bool(self._jwt),
            "jwt_preview": preview,
            "teacher_id": self._teacher_id,
            "display_name": self._display_name,
        }

    # ---------- actions ----------
    async def login(self, username: str, password: str) -> bool:
        """Async login flow. Returns True on success."""
        await self._ensure_started()
        page = self.page

        await page.goto(CONFIG.base_url, wait_until="domcontentloaded")
        await page.get_by_role("textbox", name="שם משתמש").fill(username)
        await page.get_by_role("textbox", name="סיסמה").fill(password)
        await page.get_by_role("button", name="התחברות למערכת").click()

        # settle
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except PWTimeoutError:
            pass

        # success guard: the display-name label gets non-empty value
        try:
            await page.wait_for_function(
                """(selector) => {
                    const el = document.querySelector(selector);
                    return !!(el && el.textContent && el.textContent.trim().length > 0);
                }""",
                arg=SUCCESS_LABEL_SELECTOR,
                timeout=20000,
            )
        except PWTimeoutError:
            return False

        try:
            self._display_name = (await page.locator(SUCCESS_LABEL_SELECTOR).inner_text()).strip()
        except Exception:
            self._display_name = None

        # Try to collect JWT/teacher_id
        if not self._jwt or not self._teacher_id:
            await self._harvest_jwt_from_storage()

        return True

    # ---------- API path ----------
    async def api_get_courses(self) -> List[Dict[str, Any]]:
        """
        Use captured JWT + teacher_id to call the API server-side (no CORS).
        Returns a list of course dicts (empty on failure).
        """
        if not self._jwt:
            # Try once more (in case storage got set post-login)
            await self._harvest_jwt_from_storage()
        if not self._jwt or not self._teacher_id:
            return []

        url = f"https://lmsapi.kidum-me.com/api/get-courses?teacher_id={self._teacher_id}"
        headers = {
            "Authorization": f"Bearer {self._jwt}",
            "Accept": "application/json",
            "User-Agent": "kidum-automation/1.0",
        }
        timeout = httpx.Timeout(20.0, read=20.0, connect=10.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                r = await client.get(url, headers=headers)
                r.raise_for_status()
                payload = r.json()
                if isinstance(payload, dict) and payload.get("status") and isinstance(payload.get("data"), list):
                    return payload["data"]
            except Exception:
                return []
        return []

    # ---------- dropdown (UI fallback; portal-safe) ----------
    async def _dropdown_container(self):
        page = self.page
        cont = page.locator(CONTROL_SEL)
        return cont.first if await cont.count() > 0 else page.locator("body")

    async def _wait_menu_open(self, timeout: int = 10000) -> bool:
        page = self.page
        try:
            await page.locator(MENU_SEL).first.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    async def _open_class_dropdown(self) -> None:
        page = self.page
        cont = await self._dropdown_container()

        indicator = cont.locator(INDICATOR_SEL).first
        single_value = cont.locator(SINGLE_VALUE_SEL).first
        control = cont
        inp_local = cont.locator(INPUT_SEL).first
        inp_global = page.locator(INPUT_SEL).first

        # Try clicking common targets
        for target in (indicator, single_value, control, inp_local, inp_global):
            try:
                if await target.count() == 0:
                    continue
                await target.scroll_into_view_if_needed(timeout=1500)
                await target.click()
                if await self._wait_menu_open(timeout=4000):
                    return
            except Exception:
                pass

        # Keyboard fallback: focus combobox and press keys
        for candidate in (inp_local, inp_global):
            try:
                if await candidate.count() == 0:
                    continue
                await candidate.focus()
                for key in ("ArrowDown", "Enter", " "):
                    await page.keyboard.press(key)
                    if await self._wait_menu_open(timeout=2000):
                        return
            except Exception:
                pass

        await self._debug_dump("dropdown_open_failed")
        raise RuntimeError("Failed to open class dropdown (menu did not appear).")

    async def scrape_class_options(self) -> List[Dict[str, str]]:
        await self._open_class_dropdown()
        page = self.page

        options = page.locator(OPTION_SEL)
        try:
            await options.first.wait_for(state="visible", timeout=10000)
        except Exception:
            await self._debug_dump("no_options_visible")
            return []

        out: List[Dict[str, str]] = []
        n = await options.count()
        for i in range(n):
            txt = (await options.nth(i).inner_text()).strip()
            if txt:
                out.append({"label": txt})
        if not out:
            await self._debug_dump("options_empty_texts")
        return out

    async def select_class_by_label(self, label: str) -> None:
        await self._open_class_dropdown()
        page = self.page

        option = page.locator(OPTION_SEL).filter(has_text=label).first
        if await option.count() == 0:
            await self._debug_dump("option_not_found")
            raise RuntimeError(f"Class option not found: {label}")
        await option.click()

        # Wait menu close
        try:
            await page.locator(MENU_SEL).first.wait_for(state="detached", timeout=8000)
        except Exception:
            pass

        # Best-effort: chosen text visible as singleValue
        single_value = (await self._dropdown_container()).locator(SINGLE_VALUE_SEL).first
        el = await single_value.element_handle()
        try:
            await page.wait_for_function(
                "(args) => { const [el, expected] = args; if (!el) return false; "
                "const t = (el.textContent||'').trim(); return t.includes(expected); }",
                arg=[el, label],
                timeout=8000
            )
        except Exception:
            pass

    # Convenience for fallback to names-only shape used by webapp
    async def list_classes(self) -> List[str]:
        items = await self.scrape_class_options()
        return [x["label"] for x in items if x.get("label")]
