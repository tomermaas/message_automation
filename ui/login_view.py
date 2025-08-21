from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
from PySide6.QtCore import Qt
from automation.browser import KidumSession

class LoginWindow(QWidget):
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
        self.login_btn.clicked.connect(self._on_login_clicked)

        self.status_lbl = QLabel("Enter credentials, then click Sign in.")
        self.status_lbl.setAlignment(Qt.AlignLeft)

        layout = QVBoxLayout(self)
        layout.addWidget(self.user_edit)
        layout.addWidget(self.pass_edit)
        layout.addWidget(self.login_btn)
        layout.addWidget(self.status_lbl)

        self.session: KidumSession | None = None

    def _on_login_clicked(self):
        username = self.user_edit.text().strip()
        password = self.pass_edit.text()

        if not username or not password:
            QMessageBox.warning(self, "Missing data", "Please fill username and password.")
            return

        self.status_lbl.setText("Signing in…")
        self.login_btn.setEnabled(False)

        try:
            # For Step 2 we block the UI briefly; Step 3 we'll move this to a background thread.
            self.session = KidumSession(headless=False)  # show browser while we debug
            ok = self.session.login(username, password)
            if ok:
                self.status_lbl.setText("Login successful.")
                QMessageBox.information(self, "Success", "Logged in successfully.")
            else:
                self.status_lbl.setText("Login failed.")
                QMessageBox.critical(self, "Login failed", "Invalid credentials or the site rejected the login.")
        except Exception as e:
            self.status_lbl.setText("Error during login.")
            QMessageBox.critical(self, "Error", str(e))
        finally:
            self.login_btn.setEnabled(True)
