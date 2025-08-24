from __future__ import annotations
from typing import List, Dict
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QMessageBox, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QThread
from automation.automation_worker import AutomationWorker
from app.config import CONFIG

class ClassSelectView(QWidget):
    # UI -> Worker (queued)
    request_fetch_classes = Signal()
    request_select_class = Signal(str)
    request_close = Signal()

    def __init__(self, worker: AutomationWorker, thread: QThread):
        super().__init__()
        self.setWindowTitle("Select Class – Message Automation")
        self.setMinimumWidth(520)

        self.worker = worker
        self.thread = thread
        self.options: List[Dict[str, str]] = []

        self.info_lbl = QLabel(
            f"Load classes from {CONFIG.base_url} and choose one:"
        )
        self.refresh_btn = QPushButton("Load classes")
        self.refresh_btn.clicked.connect(self._on_refresh)

        self.combo = QComboBox()
        self.combo.setEditable(False)

        self.use_btn = QPushButton("Use selected class")
        self.use_btn.clicked.connect(self._on_use)

        top = QHBoxLayout()
        top.addWidget(self.info_lbl)
        top.addStretch(1)
        top.addWidget(self.refresh_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.combo)
        layout.addWidget(self.use_btn)

        # Worker -> UI
        self.worker.classes_loaded.connect(self._on_classes_loaded)
        self.worker.classes_failed.connect(self._on_classes_failed)
        self.worker.select_class_ok.connect(self._on_select_ok)
        self.worker.select_class_failed.connect(self._on_select_failed)

        # UI -> Worker (queued)
        self.request_fetch_classes.connect(self.worker.do_fetch_classes, Qt.QueuedConnection)
        self.request_select_class.connect(self.worker.do_select_class, Qt.QueuedConnection)
        self.request_close.connect(self.worker.close, Qt.QueuedConnection)

        # Auto-load on show
        self._on_refresh()

    # ---------- lifecycle ----------
    def closeEvent(self, event):
        try:
            # Graceful shutdown of background thread when this is the last window
            if self.thread and self.thread.isRunning():
                self.request_close.emit()
                self.thread.quit()
                self.thread.wait(3000)
        finally:
            super().closeEvent(event)

    # ---------- actions ----------
    def _on_refresh(self):
        self.refresh_btn.setEnabled(False)
        self.info_lbl.setText("Loading classes…")
        self.request_fetch_classes.emit()   # QUEUED to worker thread

    def _on_use(self):
        idx = self.combo.currentIndex()
        if idx < 0 or idx >= len(self.options):
            QMessageBox.warning(self, "No selection", "Please choose a class.")
            return
        label = self.options[idx]["label"]
        self.use_btn.setEnabled(False)
        self.info_lbl.setText(f"Selecting class “{label}”…")
        self.request_select_class.emit(label)  # QUEUED to worker thread

    # ---------- results ----------
    def _on_classes_loaded(self, options_obj: object):
        try:
            options = list(options_obj)  # type: ignore
        except Exception:
            options = []
        self.options = options
        self.combo.clear()
        for o in self.options:
            self.combo.addItem(o["label"])
        self.info_lbl.setText(f"Loaded {len(self.options)} classes.")
        self.refresh_btn.setEnabled(True)

    def _on_classes_failed(self, reason: str):
        self.info_lbl.setText("Failed to load classes.")
        QMessageBox.critical(self, "Load failed", reason)
        self.refresh_btn.setEnabled(True)

    def _on_select_ok(self, label: str):
        self.info_lbl.setText(f"Selected: {label}")
        QMessageBox.information(self, "Class selected", f"Class set to: {label}")
        self.use_btn.setEnabled(True)

    def _on_select_failed(self, reason: str):
        self.info_lbl.setText("Failed to select class.")
        QMessageBox.critical(self, "Select failed", reason)
        self.use_btn.setEnabled(True)
