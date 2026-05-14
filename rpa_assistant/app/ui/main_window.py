from __future__ import annotations

import logging

from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QWidget,
)

from rpa_assistant.paths import data_paths
from rpa_assistant.app.ui.config_page import ConfigPage
from rpa_assistant.app.ui.excel_preview_page import ExcelPreviewPage
from rpa_assistant.app.ui.flow_editor_page import FlowEditorPage
from rpa_assistant.app.ui.log_page import LogPage
from rpa_assistant.app.ui.recorder_page import RecorderPage

_logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Anything Auto")
        self.resize(1100, 720)

        _root, db_path, _logs, _shots = data_paths()
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage(f"数据库：{db_path}")

        tabs = QTabWidget(self)
        tabs.addTab(ExcelPreviewPage(db_path), "数据预览")
        tabs.addTab(FlowEditorPage(), "流程")
        tabs.addTab(RecorderPage(), "录制")
        tabs.addTab(ConfigPage(db_path), "配置")
        tabs.addTab(LogPage(), "日志")
        self.setCentralWidget(tabs)

        self._build_menu()

    def _build_menu(self) -> None:
        exit_action = QAction("退出", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(QApplication.quit)

        menu = self.menuBar().addMenu("文件(&F)")
        menu.addAction(exit_action)

        help_menu = self.menuBar().addMenu("帮助(&H)")
        about = QAction("关于", self)
        about.triggered.connect(self._on_about)
        help_menu.addAction(about)

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "关于 Anything Auto",
            "跨应用 RPA 桌面助手 — MVP 开发中。\n\n"
            "数据目录可通过环境变量 ANYTHING_AUTO_DATA_DIR 覆盖。",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        _logger.info("Main window closing")
        super().closeEvent(event)
