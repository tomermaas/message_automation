from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
from PySide6.QtCore import Qt

class LoginWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("הודעות אוטומטיות לתלמדים")
        self.setMinimumWidth(420)

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("שם משתמש ל-kidum.me")

        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("סיסמא")
        self.pass_edit.setEchoMode(QLineEdit.Password)

        self.login_btn = QPushButton("Sign in")
        self.login_btn.clicked.connect(self._not_implemented)

        self.status_lbl = QLabel("Enter credentials, then click Sign in.")
        self.status_lbl.setAlignment(Qt.AlignLeft)

        layout = QVBoxLayout(self)
        layout.addWidget(self.user_edit)
        layout.addWidget(self.pass_edit)
        layout.addWidget(self.login_btn)
        layout.addWidget(self.status_lbl)

    def _not_implemented(self):
        QMessageBox.information(
            self,
            "Not implemented yet",
            "Login behavior isn’t defined.\nOnce you provide the login flow/selectors, "
            "I’ll wire it up."
        )
