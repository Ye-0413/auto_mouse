"""Run the selected flow once (no spreadsheet)."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from rpa_assistant.app.models.flow_dsl import validate_flow_definition
from rpa_assistant.paths import ensure_app_dirs
from rpa_assistant.app.storage.config_repo import ConfigRepository
from rpa_assistant.app.storage.flow_repo import FlowRepository
from rpa_assistant.app.ui.workers.single_flow_worker import SingleFlowRunWorker

_logger = logging.getLogger(__name__)


class RunPage(QWidget):
    def __init__(self, db_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db_path = Path(db_path)
        self._cfg = ConfigRepository(self._db_path)
        self._flows = FlowRepository(self._db_path)
        self._worker: SingleFlowRunWorker | None = None

        root = QVBoxLayout(self)
        self.setAccessibleName("单次运行流程")
        intro = QLabel(
            "选择要跑的<b>流程</b>，点击下方运行。每次执行会写入「日志」。"
            "<br>流程里仍可使用 <b>${变量名}</b>；当前为单次运行，变量默认为空（将由后续剪贴板分支等能力注入）。"
        )
        intro.setWordWrap(True)
        intro.setOpenExternalLinks(False)
        intro.setStyleSheet(
            "background-color: rgba(95, 175, 235, 0.12);"
            "padding: 12px; border-radius: 10px;"
            "border: 1px solid rgba(120, 185, 235, 0.28);"
            "color: #c5d8ea;",
        )
        root.addWidget(intro)

        box = QGroupBox("单次执行")
        lay = QVBoxLayout(box)
        row = QHBoxLayout()
        row.addWidget(QLabel("流程"))
        self._flow_combo = QComboBox()
        self._flow_combo.setMinimumWidth(360)
        self._flow_combo.setAccessibleName("要执行的流程")
        row.addWidget(self._flow_combo, stretch=1)
        self._btn_run = QPushButton("运行")
        self._btn_run.setObjectName("PrimaryButton")
        self._btn_run.setAccessibleName("立即运行所选流程")
        self._btn_run.clicked.connect(self._on_run)
        row.addWidget(self._btn_run)
        lay.addLayout(row)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(220)
        self._log.setPlaceholderText("运行输出会出现在这里…")
        lay.addWidget(self._log)
        root.addWidget(box, stretch=1)

        self._hint = QLabel("就绪。")
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet("color: palette(mid); padding-top: 6px;")
        root.addWidget(self._hint)

        self._reload_flows()

    def focus_default(self) -> None:
        self._flow_combo.setFocus(Qt.FocusReason.TabFocusReason)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._reload_flows()

    def _reload_flows(self) -> None:
        keep = self._flow_combo.currentData()
        self._flow_combo.blockSignals(True)
        self._flow_combo.clear()
        default_fid = None
        try:
            d = self._cfg.get_default()
            if d and d.payload.flow_id:
                default_fid = d.payload.flow_id
        except OSError:
            pass
        try:
            for f in self._flows.list_all():
                self._flow_combo.addItem(f.name, f.id)
        except OSError as exc:
            _logger.warning("Flow list failed: %s", exc)
        self._flow_combo.blockSignals(False)
        if keep:
            idx = self._flow_combo.findData(keep)
            if idx >= 0:
                self._flow_combo.setCurrentIndex(idx)
                return
        if default_fid:
            idx = self._flow_combo.findData(default_fid)
            if idx >= 0:
                self._flow_combo.setCurrentIndex(idx)

    def _set_running(self, running: bool) -> None:
        self._btn_run.setEnabled(not running)
        self._flow_combo.setEnabled(not running)

    def _on_run(self) -> None:
        fid = self._flow_combo.currentData()
        if not fid:
            QMessageBox.information(self, "运行", "请先选择一个流程。")
            return
        rec = self._flows.get(str(fid))
        if not rec:
            QMessageBox.warning(self, "运行", "所选流程不存在，请刷新后重试。")
            self._reload_flows()
            return
        steps = rec.definition.get("steps")
        if not isinstance(steps, list) or not steps:
            QMessageBox.warning(self, "运行", "该流程没有步骤。")
            return
        errs = validate_flow_definition(rec.definition)
        if errs:
            QMessageBox.warning(self, "流程无效", "\n".join(errs[:12]))
            return
        cfg = self._cfg.ensure_default()
        p = cfg.payload

        if self._worker and self._worker.isRunning():
            return

        self._log.clear()
        self._set_running(True)
        self._hint.setText("正在运行…")

        _, _, _, shots = ensure_app_dirs()
        cdp = (p.browser_cdp_url or "").strip() or None

        self._worker = SingleFlowRunWorker(
            self._db_path,
            steps=list(steps),
            flow_id=str(fid),
            config_id=cfg.id,
            variables=None,
            screenshot_on_error=bool(p.screenshot_on_error),
            screenshots_dir=shots,
            browser_cdp_url=cdp,
            parent=self,
        )
        self._worker.log_line.connect(self._log.append)
        self._worker.finished_run.connect(self._on_finished)
        self._worker.start()

    def _on_finished(self, ok: bool, err: str, eid: str) -> None:
        self._set_running(False)
        self._worker = None
        if ok:
            self._hint.setText(f"完成。执行 ID：{eid[:8]}…（可在「日志」查看明细）")
        else:
            self._hint.setText("执行失败，请查看上方输出与「日志」。")
            QMessageBox.warning(
                self,
                "失败",
                err or "流程执行失败，请查看日志中的步骤明细。",
            )
