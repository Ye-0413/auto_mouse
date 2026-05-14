from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rpa_assistant.app.storage.execution_repo import ExecutionRepository

_logger = logging.getLogger(__name__)

_HEADERS = ["状态", "流程 ID", "表行", "工作表", "开始时间", "结束时间", "说明"]


def _short_json(data: object | None, limit: int = 140) -> str:
    if data is None:
        return ""
    try:
        s = json.dumps(data, ensure_ascii=False)
    except TypeError:
        s = repr(data)
    return s if len(s) <= limit else s[: max(0, limit - 1)] + "…"


class ExecutionStepsDialog(QDialog):
    """Shows step_runs for one execution."""

    def __init__(
        self,
        db_path: Path,
        execution_id: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("执行步骤明细")
        self.resize(780, 420)
        layout = QVBoxLayout(self)
        repo = ExecutionRepository(db_path)
        try:
            runs = repo.list_step_runs(execution_id)
        except OSError as exc:
            layout.addWidget(QLabel(str(exc)))
            box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            box.rejected.connect(self.reject)
            layout.addWidget(box)
            return

        hdr = [
            "序号",
            "类型",
            "状态",
            "错误信息",
            "输出 / 入参摘要",
        ]
        table = QTableWidget(len(runs), len(hdr))
        table.setHorizontalHeaderLabels(hdr)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)

        for row_i, sr in enumerate(runs):
            oid = sr.order_index
            cells = [
                str(oid) if oid is not None else "",
                sr.step_type or "",
                sr.status.value,
                sr.error_message or "",
                _short_json(sr.output_data or sr.input_data),
            ]
            tip = ""
            if sr.input_data is not None:
                tip += "input: " + _short_json(sr.input_data, 400) + "\n"
            if sr.output_data is not None:
                tip += "output: " + _short_json(sr.output_data, 400)
            for col_i, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setToolTip(tip.strip())
                table.setItem(row_i, col_i, item)

        layout.addWidget(table)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        box.rejected.connect(self.accept)
        layout.addWidget(box)


class LogPage(QWidget):
    """Recent execution records from the local database."""

    def __init__(self, db_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db_path = Path(db_path)
        self._repo = ExecutionRepository(self._db_path)

        root = QVBoxLayout(self)
        self.setAccessibleName("执行日志")
        bar = QHBoxLayout()
        self._btn_export = QPushButton("导出 CSV…")
        self._btn_export.setToolTip("将当前列表中的执行记录导出为 UTF-8 CSV（含 Excel 友好 BOM）")
        self._btn_export.setAccessibleName("导出执行记录 CSV")
        self._btn_export.clicked.connect(self._export_csv)
        bar.addWidget(self._btn_export)
        self._hint = QLabel("双击一行可查看该次执行的步骤明细。")
        self._hint.setStyleSheet("color: palette(mid);")
        bar.addWidget(self._hint)
        bar.addStretch(1)
        root.addLayout(bar)

        self._table = QTableWidget(0, len(_HEADERS))
        self._table.setHorizontalHeaderLabels(_HEADERS)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows,
        )
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive,
        )
        self._table.setAlternatingRowColors(True)
        self._table.setAccessibleName("最近执行记录表")
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        root.addWidget(self._table)

        self._refresh()

    def focus_default(self) -> None:
        self._table.setFocus(Qt.FocusReason.TabFocusReason)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        try:
            executions = self._repo.list_recent(200)
        except OSError as exc:
            _logger.exception("Failed to list executions")
            self._table.setRowCount(1)
            self._table.setColumnCount(len(_HEADERS))
            item = QTableWidgetItem(str(exc))
            self._table.setItem(0, 0, item)
            return

        self._table.setRowCount(len(executions))
        for row_i, ex in enumerate(executions):
            file_name = ""
            if ex.source_file:
                file_name = Path(ex.source_file).name
            note = ex.error_message or ""
            if not note and ex.status.value == "running":
                note = "进行中（若界面已关闭可能为未落库结束时间）"

            cells = [
                ex.status.value,
                ex.flow_id or "",
                str(ex.source_row_index) if ex.source_row_index is not None else "",
                ex.source_sheet or "",
                ex.started_at or "",
                ex.ended_at or "",
                note,
            ]
            tip_lines = [
                f"id: {ex.id}",
                f"batch_id: {ex.batch_id}",
                f"config_id: {ex.config_id}",
                f"file: {ex.source_file or ''}",
            ]
            if ex.variables is not None:
                try:
                    tip_lines.append(
                        "variables: "
                        + json.dumps(ex.variables, ensure_ascii=False),
                    )
                except TypeError:
                    tip_lines.append(f"variables: {ex.variables!r}")
            if ex.screenshot_path:
                tip_lines.append(f"screenshot: {ex.screenshot_path}")
            tooltip = "\n".join(tip_lines)

            for col_i, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if col_i == 0 and file_name:
                    item.setToolTip(f"{tooltip}\nsource_file: {file_name}")
                else:
                    item.setToolTip(tooltip)
                if col_i == 0:
                    item.setData(Qt.ItemDataRole.UserRole, ex.id)
                self._table.setItem(row_i, col_i, item)

    def _on_cell_double_clicked(self, row: int, _column: int) -> None:
        item = self._table.item(row, 0)
        if not item:
            return
        eid = item.data(Qt.ItemDataRole.UserRole)
        if not eid:
            return
        dlg = ExecutionStepsDialog(self._db_path, str(eid), parent=self)
        dlg.exec()

    def _export_csv(self) -> None:
        try:
            executions = self._repo.list_recent(200)
        except OSError as exc:
            QMessageBox.warning(self, "导出失败", str(exc))
            return
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "导出执行记录",
            "executions.csv",
            "CSV 表格 (*.csv)",
        )
        if not path_str:
            return
        out_path = Path(path_str)
        fieldnames = [
            "id",
            "status",
            "batch_id",
            "flow_id",
            "config_id",
            "source_row_index",
            "source_sheet",
            "source_file",
            "started_at",
            "ended_at",
            "error_message",
            "screenshot_path",
            "variables_json",
        ]
        try:
            with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                w.writeheader()
                for ex in executions:
                    vars_json = ""
                    if ex.variables is not None:
                        try:
                            vars_json = json.dumps(
                                ex.variables,
                                ensure_ascii=False,
                            )
                        except TypeError:
                            vars_json = repr(ex.variables)
                    w.writerow(
                        {
                            "id": ex.id,
                            "status": ex.status.value,
                            "batch_id": ex.batch_id or "",
                            "flow_id": ex.flow_id or "",
                            "config_id": ex.config_id or "",
                            "source_row_index": ex.source_row_index
                            if ex.source_row_index is not None
                            else "",
                            "source_sheet": ex.source_sheet or "",
                            "source_file": ex.source_file or "",
                            "started_at": ex.started_at or "",
                            "ended_at": ex.ended_at or "",
                            "error_message": ex.error_message or "",
                            "screenshot_path": ex.screenshot_path or "",
                            "variables_json": vars_json,
                        },
                    )
        except OSError as exc:
            QMessageBox.warning(self, "导出失败", str(exc))
            return
        QMessageBox.information(
            self,
            "导出完成",
            f"已写入 {len(executions)} 条记录：\n{out_path}",
        )
