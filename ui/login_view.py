from __future__ import annotations
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
from PySide6.QtCore import Qt, QThread, Signal
from automation.automation_worker import AutomationWorker

def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}

class LoginWindow(QWidget):
    # Emit (username, password, headless_or_None) to run in worker thread
    request_login = Signal(str, str, object)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Message Automation")
        self.setMinimumWidth(420)

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("Username or Email")

        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("Password")
        self.pass_edit.setEchoMode(QLineEdit.Password)

        self.login_btn = QPushButton("Sign in")
        self.login_btn.clicked.connect(self._start_login_bg)

        self.status_lbl = QLabel("Enter credentials, then click Sign in.")
        self.status_lbl.setAlignment(Qt.AlignLeft)

        layout = QVBoxLayout(self)
        layout.addWidget(self.user_edit)
        layout.addWidget(self.pass_edit)
        layout.addWidget(self.login_btn)
        layout.addWidget(self.status_lbl)

        # Background automation thread & worker
        self._thread: QThread | None = None
        self._worker: AutomationWorker | None = None

        self._ensure_thread()

    # ---------- life-cycle ----------
    def _ensure_thread(self):
        if self._thread is not None:
            return
        self._thread = QThread(self)
        self._worker = AutomationWorker()
        self._worker.moveToThread(self._thread)

        # Worker -> UI signals
        self._worker.login_ok.connect(self._on_login_ok)
        self._worker.login_failed.connect(self._on_login_failed)
        self._worker.fatal_error.connect(self._on_login_error)

        # UI -> Worker signal (queued to worker thread)
        # Qt.QueuedConnection is implicit across threads, but being explicit is fine.
        self.request_login.connect(self._worker.do_login, Qt.QueuedConnection)

        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def closeEvent(self, event):
        try:
            if self._worker:
                self._worker.close()
            if self._thread:
                self._thread.quit()
                self._thread.wait(3000)
        finally:
            super().closeEvent(event)

    # ---------- actions ----------
    def _start_login_bg(self):
        username = self.user_edit.text().strip()
        password = self.pass_edit.text()
        if not username or not password:
            QMessageBox.warning(self, "Missing data", "Please fill username and password.")
            return

        self.status_lbl.setText("Signing in… (running in background)")
        self.login_btn.setEnabled(False)

        headless = _env_bool("PLAYWRIGHT_HEADLESS", True)
        # Queue the job on the worker thread (non-blocking)
        self.request_login.emit(username, password, headless)

    # ---------- results ----------
    def _on_login_ok(self, display_name: str):
        self.status_lbl.setText(f"Login successful. User: {display_name or '—'}")
        QMessageBox.information(self, "Success", f"Logged in as: {display_name or '—'}")
        self.login_btn.setEnabled(True)

    def _on_login_failed(self, reason: str):
        self.status_lbl.setText("Login failed.")
        QMessageBox.critical(self, "Login failed", reason)
        self.login_btn.setEnabled(True)

    def _on_login_error(self, err: str):
        self.status_lbl.setText("Error during login.")
        QMessageBox.critical(self, "Error", err)
        self.login_btn.setEnabled(True)
