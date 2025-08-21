from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication
from app.logging_conf import setup_logging
from ui.login_view import LoginWindow

def main() -> None:
    setup_logging()
    app = QApplication(sys.argv)
    win = LoginWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
