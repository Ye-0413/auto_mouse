from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from rpa_assistant.app.bootstrap import bootstrap_application
from rpa_assistant.app.ui.main_window import MainWindow


def main() -> int:
    bootstrap_application()
    app = QApplication(sys.argv)
    app.setApplicationName("Anything Auto")
    app.setOrganizationName("AnythingAuto")

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
