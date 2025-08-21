from __future__ import annotations
import os
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal

from automation.automation_worker import AutomationWorker
from ui.class_select_view import ClassSelectView


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


class LoginWindow(QWidget):
    # UI -> Worker (queued)
    request_login = Signal(str, str, object)
    request_close = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Message Automation")
        self.setMinimumWidth(520)

        # --- login widgets ---
        self.user_edit = QLineEdit(placeholderText="Username or Email")
        self.pass_edit = QLineEdit(placeholderText="Password")
        self.pass_edit.setEchoMode(QLineEdit.Password)

        self.login_btn = QPushButton("Sign in")
        self.login_btn.clicked.connect(self._start_login_bg)

        self.status_lbl = QLabel("Enter credentials, then click Sign in.")
        self.status_lbl.setAlignment(Qt.AlignLeft)

        # root layout (we will swap its contents after login)
        self._root = QVBoxLayout(self)
        self._root.addWidget(self.user_edit)
        self._root.addWidget(self.pass_edit)
        self._root.addWidget(self.login_btn)
        self._root.addWidget(self.status_lbl)

        # background automation thread/worker
        self._thread: QThread | None = None
        self._worker: AutomationWorker | None = None
        self._class_view: Optional[ClassSelectView] = None

        self._ensure_thread()

    # ---------- thread lifecycle ----------
    def _ensure_thread(self):
        if self._thread is not None:
            return
        # No parent: thread remains alive until we quit it
        self._thread = QThread()
        self._worker = AutomationWorker()
        self._worker.moveToThread(self._thread)

        # Worker -> UI
        self._worker.login_ok.connect(self._on_login_ok)
        self._worker.login_failed.connect(self._on_login_failed)
        self._worker.fatal_error.connect(self._on_login_error)

        # UI -> Worker (queued)
        self.request_login.connect(self._worker.do_login, Qt.QueuedConnection)
        self.request_close.connect(self._worker.close, Qt.QueuedConnection)

        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def closeEvent(self, event):
        # Always shut down background thread when the main window closes
        try:
            if self._worker and self._thread:
                self.request_close.emit()
                self._thread.quit()
                self._thread.wait(3000)
        finally:
            super().closeEvent(event)

    # ---------- login flow ----------
    def _start_login_bg(self):
        username = self.user_edit.text().strip()
        password = self.pass_edit.text()
        if not username or not password:
            QMessageBox.warning(self, "Missing data", "Please fill username and password.")
            return

        self.status_lbl.setText("Signing in… (running in background)")
        self.login_btn.setEnabled(False)

        headless = _env_bool("PLAYWRIGHT_HEADLESS", True)
        self.request_login.emit(username, password, headless)

    def _on_login_ok(self, display_name: str):
        self.status_lbl.setText(f"Login successful. User: {display_name or '—'}")
        QMessageBox.information(self, "Success", f"Logged in as: {display_name or '—'}")
        self.login_btn.setEnabled(True)

        # ----- SWAP CONTENT IN THE SAME WINDOW -----
        # Clear current login widgets from the root layout
        for i in reversed(range(self._root.count())):
            item = self._root.itemAt(i)
            w = item.widget()
            if w is not None:
                w.setParent(None)
            self._root.removeItem(item)

        # Embed ClassSelectView inside this same window
        self._class_view = ClassSelectView(worker=self._worker, thread=self._thread)  # type: ignore[arg-type]
        self._root.addWidget(self._class_view)
        self.setWindowTitle("Select Class – Message Automation")

    def _on_login_failed(self, reason: str):
        self.status_lbl.setText("Login failed.")
        QMessageBox.critical(self, "Login failed", reason)
        self.login_btn.setEnabled(True)

    def _on_login_error(self, err: str):
        self.status_lbl.setText("Error during login.")
        QMessageBox.critical(self, "Error", err)
        self.login_btn.setEnabled(True)
