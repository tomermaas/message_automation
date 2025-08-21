from __future__ import annotations
from typing import Optional, List, Dict
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Locator
from app.config import CONFIG
import os
from .browser_async import AsyncKidumSession as KidumSession

SUCCESS_LABEL_SELECTOR = 'label[for="select-placeholder"]'

# Narrow scope to the header/course dropdown
COURSE_DROPDOWN_CONTAINER = "div.course-dropdown.custom-select-control"

class AsyncKidumSession:
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


# ---------- debug ----------
def _debug_dump(self, tag: str) -> None:
    """Save a full-page screenshot and HTML for troubleshooting."""
    try:
        os.makedirs("data/sample", exist_ok=True)
        self.page.screenshot(path=f"data/sample/{tag}.png", full_page=True)
        with open(f"data/sample/{tag}.html", "w", encoding="utf-8") as f:
            f.write(self.page.content())
    except Exception:
        pass


# ---------- class dropdown helpers ----------
def _dropdown_container(self):
    page = self.page
    cont = page.locator(COURSE_DROPDOWN_CONTAINER)
    if cont.count() == 0:
        cont = page.locator("div.headerDropdown.custom-select-control, div.custom-select-control")
    # If still none, we’ll work globally; don’t raise here.
    return cont.first if cont.count() > 0 else page.locator("body")  # fallback scope


def _wait_menu_open(self, timeout: int = 10000) -> bool:
    page = self.page
    try:
        # react-select portals menu to body → wait globally
        menu = page.locator('div[id^="react-select-"][id$="-listbox"]').first
        menu.wait_for(state="visible", timeout=timeout)
        return True
    except PWTimeoutError:
        return False


def _open_class_dropdown(self) -> None:
    """
    Open the dropdown using several strategies, incl. sending ArrowDown
    to the react-select input.
    """
    page = self.page
    cont = self._dropdown_container()

    # Candidate click targets (most reliable first)
    candidates = [
        cont.locator("div[class*='singleValue']").first,  # visible current value
        cont.locator("div[class*='__control'], div[class*='control']").first,  # control wrapper
        cont.get_by_role("combobox").first,  # ARIA
        cont.locator('input[id^="react-select-"][id$="-input"]').first,  # input in control
        page.locator('input[id^="react-select-"][id$="-input"]').first,  # global fallback
    ]

    # Try clicking each candidate, then check if menu opened
    for target in candidates:
        try:
            if target.count() == 0:
                continue
            target.scroll_into_view_if_needed(timeout=1500)
            target.click()
            if self._wait_menu_open(timeout=4000):
                return
        except Exception:
            pass

    # If click didn’t work, try focusing the input and pressing ArrowDown
    try_inputs = [
        cont.locator('input[id^="react-select-"][id$="-input"]').first,
        page.locator('input[id^="react-select-"][id$="-input"]').first,
    ]
    for inp in try_inputs:
        try:
            if inp.count() == 0:
                continue
            inp.focus()
            page.keyboard.press("ArrowDown")
            if self._wait_menu_open(timeout=4000):
                return
            # Try Enter too (sometimes needed)
            page.keyboard.press("Enter")
            if self._wait_menu_open(timeout=4000):
                return
        except Exception:
            pass

    # As a last attempt, click anywhere on known custom-select container globally
    try:
        any_control = page.locator("div.custom-select-control, div[class*='__control']").first
        if any_control.count() > 0:
            any_control.click()
            if self._wait_menu_open(timeout=4000):
                return
    except Exception:
        pass

    self._debug_dump("dropdown_open_failed")
    raise RuntimeError("Failed to open class dropdown (menu did not appear).")


def scrape_class_options(self) -> List[Dict[str, str]]:
    """Return [{label: '...'}] for each option."""
    self._open_class_dropdown()
    page = self.page

    option_loc = page.locator('div[id^="react-select-"][id$="-option-"]')
    try:
        option_loc.first.wait_for(state="visible", timeout=10000)
    except PWTimeoutError:
        self._debug_dump("no_options_visible")
        return []

    labels: List[Dict[str, str]] = []
    count = option_loc.count()
    for i in range(count):
        txt = option_loc.nth(i).inner_text().strip()
        if txt:
            labels.append({"label": txt})
    if not labels:
        self._debug_dump("options_empty_texts")
    return labels


def select_class_by_label(self, label: str) -> None:
    self._open_class_dropdown()
    page = self.page

    option = page.locator('div[id^="react-select-"][id$="-option-"]', has_text=label).first
    if option.count() == 0:
        option = page.locator('div[id^="react-select-"][id$="-option-"]').filter(has_text=label).first
    if option.count() == 0:
        self._debug_dump("option_not_found")
        raise RuntimeError(f"Class option not found: {label}")
    option.click()

    # Wait for menu to close
    try:
        page.locator('div[id^="react-select-"][id$="-listbox"]').first.wait_for(state="detached", timeout=8000)
    except PWTimeoutError:
        pass

    # Best-effort: wait until some visible singleValue includes the label
    single_value = page.locator("div[class*='singleValue']").first
    try:
        page.wait_for_function(
            """(el, expected) => el && el.textContent && el.textContent.trim().includes(expected)""",
            arg=[single_value.element_handle(), label],
            timeout=8000,
        )
    except Exception:
        # Non-fatal; selection likely applied.
        pass
