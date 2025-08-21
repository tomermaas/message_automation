from __future__ import annotations
from typing import Optional
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from app.config import CONFIG

SUCCESS_LABEL_SELECTOR = 'label[for="select-placeholder"]'

class KidumSession:
    """
    Minimal sync Playwright session that stays open after login.
    """
    def __init__(self, headless: Optional[bool] = None):
        self._pw = None
        self._browser = None
        self._page = None
        self._headless = CONFIG.headless if headless is None else headless
        self._display_name: Optional[str] = None

    # ---------- lifecycle ----------
    def _ensure_started(self):
        if self._browser is not None:
            return
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self._headless)
        self._page = self._browser.new_page()
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
        Fills:
          - username textbox (role name: 'שם משתמש')
          - password textbox (role name: 'סיסמה')
          - submit button (role name: 'התחברות למערכת')
        Success = SUCCESS_LABEL_SELECTOR exists and its text is non-empty.
        """
        self._ensure_started()
        page = self._page

        page.goto(CONFIG.base_url, wait_until="domcontentloaded")

        user_tb = page.get_by_role("textbox", name="שם משתמש")
        pass_tb = page.get_by_role("textbox", name="סיסמה")
        submit_btn = page.get_by_role("button", name="התחברות למערכת")

        user_tb.click()
        user_tb.fill(username)
        pass_tb.click()
        pass_tb.fill(password)
        submit_btn.click()

        # Wait for network calm a bit (non-fatal if it times out)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeoutError:
            pass

        # Wait until the success label has non-empty trimmed text
        try:
            page.wait_for_function(
                """(selector) => {
                    const el = document.querySelector(selector);
                    return !!(el && el.textContent && el.textContent.trim().length > 0);
                }""",
                arg=SUCCESS_LABEL_SELECTOR,
                timeout=15000,
            )
        except PWTimeoutError:
            return False

        # Cache the display name for later use
        try:
            self._display_name = page.locator(SUCCESS_LABEL_SELECTOR).inner_text().strip()
        except Exception:
            self._display_name = None

        return True

    @property
    def page(self):
        self._ensure_started()
        return self._page

    def get_logged_in_display_name(self) -> Optional[str]:
        return self._display_name
