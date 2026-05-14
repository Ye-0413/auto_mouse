"""Minimal desktop recorder tab (optional ``pynput``)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rpa_assistant.app.models.common import FlowStatus
from rpa_assistant.app.models.flow_dsl import validate_flow_definition
from rpa_assistant.app.recording.recorder_thread import RecorderThread
from rpa_assistant.app.storage.flow_repo import FlowRepository
from rpa_assistant.app.ui.flow.presentation import step_type_label, summarize_step


class RecorderPage(QWidget):
    """Records ``click_mouse``, batched ``input_text``, and ``hotkey`` steps locally."""

    def __init__(self, db_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db_path = Path(db_path)
        self._flows = FlowRepository(self._db_path)
        self._thread: RecorderThread | None = None
        self._captured: list[dict] = []

        layout = QVBoxLayout(self)

        intro = QLabel(
            "在后台线程捕获本机输入事件（不上传、不 eval）。需安装 pynput。\n"
            "左键单击记录为坐标点击；普通打字合并为「输入文字」；带 Ctrl/Alt/Cmd 的组合键记录为快捷键。\n"
            "坐标在不同分辨率下可能失效，录制后请在「流程」页微调。",
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: palette(mid); padding: 4px 0;")
        layout.addWidget(intro)

        ctrl = QHBoxLayout()
        self._btn_start = QPushButton("开始录制")
        self._btn_start.clicked.connect(self._on_start)
        self._btn_stop = QPushButton("停止")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_clear = QPushButton("清空列表")
        self._btn_clear.clicked.connect(self._on_clear)
        for b in (self._btn_start, self._btn_stop, self._btn_clear):
            ctrl.addWidget(b)
        ctrl.addStretch(1)
        layout.addLayout(ctrl)

        save_box = QGroupBox("保存到流程")
        save_lay = QGridLayout(save_box)
        save_lay.addWidget(QLabel("新建流程名称"), 0, 0)
        self._new_name = QLineEdit()
        self._new_name.setPlaceholderText("保存为新流程时使用")
        save_lay.addWidget(self._new_name, 0, 1)
        save_lay.addWidget(QLabel("追加到已有流程"), 1, 0)
        self._flow_combo = QComboBox()
        self._flow_combo.setMinimumWidth(280)
        save_lay.addWidget(self._flow_combo, 1, 1)
        btn_row = QHBoxLayout()
        self._btn_save_new = QPushButton("保存为新流程")
        self._btn_save_new.clicked.connect(self._on_save_new)
        self._btn_append = QPushButton("追加到所选流程")
        self._btn_append.clicked.connect(self._on_append)
        btn_row.addWidget(self._btn_save_new)
        btn_row.addWidget(self._btn_append)
        btn_row.addStretch(1)
        save_lay.addLayout(btn_row, 2, 0, 1, 2)
        layout.addWidget(save_box)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["顺序", "类型", "说明"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, stretch=1)

        self._hint = QLabel("就绪。")
        self._hint.setWordWrap(True)
        layout.addWidget(self._hint)

        self._reload_flow_combo()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._reload_flow_combo()

    def _reload_flow_combo(self) -> None:
        keep = self._flow_combo.currentData()
        self._flow_combo.blockSignals(True)
        self._flow_combo.clear()
        for r in self._flows.list_all():
            self._flow_combo.addItem(f"{r.name} ({r.id[:8]}…)", r.id)
        self._flow_combo.blockSignals(False)
        if keep:
            idx = self._flow_combo.findData(keep)
            if idx >= 0:
                self._flow_combo.setCurrentIndex(idx)

    def _set_recording_ui(self, active: bool) -> None:
        self._btn_start.setEnabled(not active)
        self._btn_stop.setEnabled(active)

    def _on_start(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            QMessageBox.information(self, "录制", "已在录制中。")
            return
        try:
            import pynput  # noqa: F401
        except ImportError:
            QMessageBox.warning(
                self,
                "缺少依赖",
                "未安装 pynput，无法录制。\n\n请执行：\npip install pynput\n\n"
                "或安装可选依赖：pip install \"anything-auto[recorder]\"",
            )
            return

        self._thread = RecorderThread(self)
        self._thread.step_captured.connect(self._on_step_captured)
        self._thread.import_failed.connect(self._on_import_failed)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()
        self._set_recording_ui(True)
        self._hint.setText("正在录制…点击「停止」结束。")

    def _on_import_failed(self, msg: str) -> None:
        QMessageBox.warning(self, "录制不可用", msg)
        self._set_recording_ui(False)

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._set_recording_ui(False)
        self._hint.setText(f"已停止。当前列表 {len(self._captured)} 步。")

    def _on_stop(self) -> None:
        if self._thread is None or not self._thread.isRunning():
            self._set_recording_ui(False)
            return
        self._thread.request_stop()
        self._hint.setText("正在停止监听器…")
        if not self._thread.wait(8_000):
            self._hint.setText("停止超时，请稍候或重启应用。")

    def _on_step_captured(self, step: dict) -> None:
        self._captured.append(step)
        self._refresh_table()
        self._hint.setText(f"录制中…已捕获 {len(self._captured)} 步。")

    def _refresh_table(self) -> None:
        self._table.setRowCount(len(self._captured))
        for i, step in enumerate(self._captured):
            t = step.get("type", "")
            self._table.setItem(i, 0, self._ro(str(i + 1)))
            self._table.setItem(i, 1, self._ro(step_type_label(t)))
            self._table.setItem(i, 2, self._ro(summarize_step(step)))

    def _ro(self, text: str) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        return it

    def _on_clear(self) -> None:
        self._captured.clear()
        self._refresh_table()
        self._hint.setText("列表已清空。")

    def _on_save_new(self) -> None:
        if not self._captured:
            QMessageBox.information(self, "保存", "当前没有录制的步骤。")
            return
        name = self._new_name.text().strip() or "录制流程"
        definition = {"steps": [dict(s) for s in self._captured]}
        errs = validate_flow_definition(definition)
        if errs:
            QMessageBox.warning(self, "无法保存", "\n".join(errs[:12]))
            return
        fid = self._flows.create(name, definition, status=FlowStatus.DRAFT)
        self._new_name.clear()
        self._captured.clear()
        self._refresh_table()
        self._reload_flow_combo()
        idx = self._flow_combo.findData(fid)
        if idx >= 0:
            self._flow_combo.setCurrentIndex(idx)
        self._hint.setText(f"已新建流程「{name}」。")

    def _on_append(self) -> None:
        if not self._captured:
            QMessageBox.information(self, "追加", "当前没有录制的步骤。")
            return
        fid = self._flow_combo.currentData()
        if not fid:
            QMessageBox.information(self, "追加", "请先在列表中选择要追加的流程。")
            return
        rec = self._flows.get(str(fid))
        if not rec:
            QMessageBox.warning(self, "追加", "所选流程不存在，请刷新后重试。")
            self._reload_flow_combo()
            return
        raw = rec.definition.get("steps")
        existing = [dict(s) for s in raw] if isinstance(raw, list) else []
        merged = existing + [dict(s) for s in self._captured]
        definition = {"steps": merged}
        errs = validate_flow_definition(definition)
        if errs:
            QMessageBox.warning(self, "无法保存", "\n".join(errs[:12]))
            return
        rec.definition = definition
        self._flows.save(rec)
        self._captured.clear()
        self._refresh_table()
        self._hint.setText(f"已追加到「{rec.name}」。")
