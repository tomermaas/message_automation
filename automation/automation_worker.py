from __future__ import annotations
from typing import Optional, List, Dict, Any
from PySide6.QtCore import QObject, Signal, Slot
import asyncio
from automation.api_client import KidumApiSession

class AutomationWorker(QObject):
    """
    Lives in its own QThread. Owns the KidumApiSession so all API calls
    happen off the UI thread.
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
        self.session: Optional[KidumApiSession] = None
        self._courses: List[Dict[str, Any]] = []

    # ---------- Login ----------
    @Slot(str, str)
    def do_login(self, username: str, password: str) -> None:
        try:
            self.session = KidumApiSession()
            ok = asyncio.run(self.session.login(username, password))
            if not ok:
                asyncio.run(self.session.close())
                self.session = None
                self.login_failed.emit("Invalid credentials or API error.")
                return
            name = (self.session.get_logged_in_display_name() or "").strip()
            self.login_ok.emit(name)
        except Exception as e:
            try:
                if self.session:
                    asyncio.run(self.session.close())
            finally:
                self.session = None
            self.fatal_error.emit(str(e))

    @Slot()
    def close(self) -> None:
        if self.session:
            asyncio.run(self.session.close())
            self.session = None

    # ---------- Classes ----------
    @Slot()
    def do_fetch_classes(self) -> None:
        if not self.session:
            self.classes_failed.emit("Not logged in.")
            return
        try:
            raw = asyncio.run(self.session.api_get_courses())
            self._courses = []
            options = []
            for row in raw or []:
                cid = row.get("course_id") or row.get("id") or (row.get("courses") or {}).get("id")
                name = row.get("name") or (row.get("courses") or {}).get("name")
                if cid and name:
                    try:
                        cid = int(cid)
                    except Exception:
                        pass
                    self._courses.append({"id": cid, "name": name})
                    options.append({"label": name})
            if not options:
                self.classes_failed.emit("No classes found.")
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
            for c in self._courses:
                if c["name"] == label:
                    self.session.set_selected_course_id(c["id"])
                    self.select_class_ok.emit(label)
                    return
            self.select_class_failed.emit("Class not found")
        except Exception as e:
            self.select_class_failed.emit(str(e))
