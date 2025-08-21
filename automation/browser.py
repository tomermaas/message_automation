from __future__ import annotations
from typing import Optional
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from app.config import CONFIG

class KidumSession:
    """
    A minimal, stateful Playwright session (sync API) that stays open after login.
    """

    def __init__(self, headless: Optional[bool] = None):
        self._pw = None
        self._browser = None
        self._page = None
        self._headless = CONFIG.headless if headless is None else headless

    # ---------- lifecycle ----------
    def _ensure_started(self):
        if self._browser is not None:
            return
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self._headless)
        self._page = self._browser.new_page()
        # Reasonable default timeouts
        self._page.set_default_timeout(15000)

    def close(self):
        try:
            if self._browser:
                self._browser.close()
        finally:
            self._browser = None
            if self._pw:
                self._pw.stop()
                self._pw = None
            self._page = None

    # ---------- actions ----------
    def login(self, username: str, password: str) -> bool:
        """
        Logs into https://kidum-me.com/ using the selectors you provided:
          - username textbox (role): 'שם משתמש'
          - password textbox (role): 'סיסמה'
          - submit button (role): 'התחברות למערכת'

        Heuristic success check:
          - After clicking submit, wait for network idle; if the login button and both inputs
            are NOT visible anymore, we consider it a success.
        """
        self._ensure_started()
        page = self._page

        # Open homepage
        page.goto(CONFIG.base_url, wait_until="domcontentloaded")

        # Fill credentials (roles and accessible names from your codegen)
        user_tb = page.get_by_role("textbox", name="שם משתמש")
        pass_tb = page.get_by_role("textbox", name="סיסמה")
        submit_btn = page.get_by_role("button", name="התחברות למערכת")

        user_tb.click()
        user_tb.fill(username)
        pass_tb.click()
        pass_tb.fill(password)
        submit_btn.click()

        # Wait for network quietness after submit
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeoutError:
            # continue to heuristic checks
            pass

        # Heuristic: if login controls are still visible, likely failed
        try:
            still_has_login_controls = (
                submit_btn.is_visible()
                and user_tb.is_visible()
                and pass_tb.is_visible()
            )
            if still_has_login_controls:
                return False
        except Exception:
            # If querying those elements fails (detached), it likely navigated away -> success
            pass

        # If needed, you can add a URL-based guard here once you provide it:
        #   page.wait_for_url("**/home/**", timeout=10000)

        return True

    # Keep for future extractors (will use self._page)
    @property
    def page(self):
        self._ensure_started()
        return self._page
