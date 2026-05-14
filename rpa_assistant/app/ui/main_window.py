from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QStackedWidget,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from rpa_assistant.paths import data_paths
from rpa_assistant.app.ui.accessibility import announce_status
from rpa_assistant.app.ui.config_page import ConfigPage
from rpa_assistant.app.ui.flow_editor_page import FlowEditorPage
from rpa_assistant.app.ui.log_page import LogPage
from rpa_assistant.app.ui.recorder_page import RecorderPage
from rpa_assistant.app.ui.run_page import RunPage

_logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Anything Auto")
        self.resize(1240, 780)
        self.setMinimumSize(980, 640)

        _root, db_path, _logs, _shots = data_paths()
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage(f"就绪 · {db_path}")

        self._run_page = RunPage(db_path)
        self._flow_page = FlowEditorPage(db_path)
        self._recorder_page = RecorderPage(db_path)
        self._config_page = ConfigPage(db_path)
        self._log_page = LogPage(db_path)

        shell = QWidget()
        root_lay = QHBoxLayout(shell)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(228)
        side_lay = QVBoxLayout(sidebar)
        side_lay.setContentsMargins(16, 22, 12, 20)
        side_lay.setSpacing(8)

        brand_title = QLabel("Anything Auto")
        brand_title.setObjectName("BrandTitle")
        bf = brand_title.font()
        bf.setPointSize(17)
        bf.setWeight(QFont.Weight.DemiBold)
        brand_title.setFont(bf)
        tagline = QLabel("桌面自动化工作台")
        tagline.setObjectName("BrandTagline")
        side_lay.addWidget(brand_title)
        side_lay.addWidget(tagline)

        self._nav = QListWidget()
        self._nav.setObjectName("SideNav")
        self._nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._nav.setSpacing(2)
        self._nav.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._pages_meta = [
            ("运行", "单次执行已保存的流程", self._run_page),
            ("流程", "步骤编排与变量替换", self._flow_page),
            ("录制", "捕获操作生成步骤", self._recorder_page),
            ("配置", "默认流程与运行选项", self._config_page),
            ("日志", "执行轨迹与导出", self._log_page),
        ]
        for title, sub, _w in self._pages_meta:
            it = QListWidgetItem(title)
            it.setToolTip(f"{title}\n{sub}")
            self._nav.addItem(it)

        self._nav.currentRowChanged.connect(self._on_section_changed)
        side_lay.addWidget(self._nav, stretch=1)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        spacer.setMinimumHeight(4)
        side_lay.addWidget(spacer)

        help_btn = QPushButton("帮助与快捷键…")
        help_btn.setFlat(True)
        help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        help_btn.clicked.connect(self._on_shortcuts_help)
        help_btn.setStyleSheet(
            "QPushButton { color: #7d8ea1; padding: 6px 10px; text-align: left; "
            "border: none; border-radius: 8px; }"
            "QPushButton:hover { color: #b8cce0; background: #161d24; }",
        )
        side_lay.addWidget(help_btn)

        divider = QFrame()
        divider.setObjectName("SidebarDivider")
        root_lay.addWidget(sidebar)
        root_lay.addWidget(divider)

        content_outer = QFrame()
        content_outer.setObjectName("ContentShell")
        content_lay = QVBoxLayout(content_outer)
        content_lay.setContentsMargins(28, 24, 28, 20)
        content_lay.setSpacing(10)

        self._page_title = QLabel("")
        self._page_title.setObjectName("PageTitle")
        tf = self._page_title.font()
        tf.setPointSize(20)
        tf.setWeight(QFont.Weight.DemiBold)
        self._page_title.setFont(tf)
        self._page_subtitle = QLabel("")
        self._page_subtitle.setObjectName("PageSubtitle")

        header = QVBoxLayout()
        header.setSpacing(4)
        header.addWidget(self._page_title)
        header.addWidget(self._page_subtitle)
        content_lay.addLayout(header)

        self._stack = QStackedWidget()
        for _, _, widget in self._pages_meta:
            self._stack.addWidget(widget)
        content_lay.addWidget(self._stack, stretch=1)

        root_lay.addWidget(content_outer, stretch=1)
        self.setCentralWidget(shell)

        self._nav.setCurrentRow(0)
        self._on_section_changed(0)

        sc_rec = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        sc_rec.setContext(Qt.ShortcutContext.ApplicationShortcut)
        sc_rec.activated.connect(self._recorder_page.trigger_shortcut_start)
        sc_stop = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        sc_stop.setContext(Qt.ShortcutContext.ApplicationShortcut)
        sc_stop.activated.connect(self._recorder_page.trigger_shortcut_stop)

        self._build_menu()

    def _on_section_changed(self, row: int) -> None:
        if row < 0:
            return
        self._stack.setCurrentIndex(row)
        title, subtitle, page = self._pages_meta[row]
        self._page_title.setText(title)
        self._page_subtitle.setText(subtitle)
        focus_fn = getattr(page, "focus_default", None)
        if callable(focus_fn):
            focus_fn()
        announce_status(page, f"已切换到{title}：{subtitle}")

    def _build_menu(self) -> None:
        exit_action = QAction("退出", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(QApplication.quit)

        menu = self.menuBar().addMenu("文件(&F)")
        menu.addAction(exit_action)

        help_menu = self.menuBar().addMenu("帮助(&H)")
        shortcuts = QAction("录制快捷键…", self)
        shortcuts.triggered.connect(self._on_shortcuts_help)
        help_menu.addAction(shortcuts)
        about = QAction("关于", self)
        about.triggered.connect(self._on_about)
        help_menu.addAction(about)

    def _on_shortcuts_help(self) -> None:
        QMessageBox.information(
            self,
            "快捷键",
            "开始录制：Ctrl + Shift + R\n"
            "停止录制：Ctrl + Shift + S\n"
            "录制中也可按 F12 立即停止（无须切回本窗口）",
        )

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "关于 Anything Auto",
            "跨应用 RPA 桌面助手。\n\n"
            "数据目录可由环境变量 ANYTHING_AUTO_DATA_DIR 指定。\n\n"
            "剪贴板多分支规划中：任一关键词不匹配时流程将终止（静默结束）。",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        _logger.info("Main window closing")
        super().closeEvent(event)
