from __future__ import annotations
from typing import Optional
from PySide6.QtCore import QObject, Signal, Slot
from automation.browser import KidumSession

class AutomationWorker(QObject):
    """
    Lives in its own QThread. Owns the KidumSession so all browser
    actions happen off the UI thread.
    """
    login_ok = Signal(str)          # display name (may be empty)
    login_failed = Signal(str)      # human-readable reason
    fatal_error = Signal(str)       # unexpected exception text

    def __init__(self) -> None:
        super().__init__()
        self.session: Optional[KidumSession] = None

    @Slot(str, str, object)  # (username, password, headless_or_None)
    def do_login(self, username: str, password: str, headless: Optional[bool] = None) -> None:
        try:
            self.session = KidumSession(headless=headless)  # falls back to CONFIG.headless if None
            ok = self.session.login(username, password)
            if not ok:
                # tidy up if login failed
                self.session.close()
                self.session = None
                self.login_failed.emit("Invalid credentials or success guard not found.")
                return

            name = (self.session.get_logged_in_display_name() or "").strip()
            self.login_ok.emit(name)
        except Exception as e:
            # if session was partially started, close it
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
