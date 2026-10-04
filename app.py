"""QuoteBatch Studio entry point.

Run with:  python app.py
"""
from __future__ import annotations

import multiprocessing as mp
import sys


def main():
    from PySide6.QtWidgets import QApplication

    from core.paths import ensure_user_dirs
    from ui.main_window import MainWindow
    from ui.theme import QSS

    ensure_user_dirs()

    app = QApplication(sys.argv)
    app.setApplicationName("QuoteBatch Studio")
    app.setStyleSheet(QSS)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    mp.freeze_support()  # required for the multiprocessing batch workers when packaged as a Windows .exe
    main()
