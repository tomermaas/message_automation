from __future__ import annotations
from typing import Optional, List, Dict
from PySide6.QtCore import QObject, Signal, Slot
from automation.browser_async import AsyncKidumSession

class AutomationWorker(QObject):
    """
    Lives in its own QThread. Owns the AsyncKidumSession so all browser
    actions happen off the UI thread.
    """
    login_ok = Signal(str)          # display name
    login_failed = Signal(str)
    fatal_error = Signal(str)

    classes_loaded = Signal(object)  # List[Dict[str, str]] -> [{"label": "..."}]
    classes_failed = Signal(str)

    select_class_ok = Signal(str)    # label selected
    select_class_failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.session: Optional[AsyncKidumSession] = None

    # ---------- Login ----------
    @Slot(str, str, object)  # (username, password, headless)
    def do_login(self, username: str, password: str, headless: Optional[bool] = None) -> None:
        try:
            self.session = AsyncKidumSession(headless=headless)
            ok = self.session.login(username, password)
            if not ok:
                self.session.close()
                self.session = None
                self.login_failed.emit("Invalid credentials or success guard not found.")
                return
            name = (self.session.get_logged_in_display_name() or "").strip()
            self.login_ok.emit(name)
        except Exception as e:
            try:
                if self.session:
                    self.session.close()
            finally:
                self.session = None
            self.fatal_error.emit(str(e))

    @Slot()
    def close(self) -> None:
        if self.session:
            self.session.close()
            self.session = None

    # ---------- Classes ----------
    @Slot()
    def do_fetch_classes(self) -> None:
        if not self.session:
            self.classes_failed.emit("Not logged in.")
            return
        try:
            options = self.session.scrape_class_options()
            if not options:
                self.classes_failed.emit("No classes found in the dropdown.")
                return
            self.classes_loaded.emit(options)
        except Exception as e:
            self.classes_failed.emit(str(e))

    @Slot(str)
    def do_select_class(self, label: str) -> None:
        if not self.session:
            self.select_class_failed.emit("Not logged in.")
            return
        try:
            self.session.select_class_by_label(label)
            self.select_class_ok.emit(label)
        except Exception as e:
            self.select_class_failed.emit(str(e))
