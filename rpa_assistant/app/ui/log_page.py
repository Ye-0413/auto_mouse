from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rpa_assistant.app.storage.execution_repo import ExecutionRepository

_logger = logging.getLogger(__name__)

_HEADERS = ["状态", "流程 ID", "表行", "工作表", "开始时间", "结束时间", "说明"]


class LogPage(QWidget):
    """Recent execution records from the local database."""

    def __init__(self, db_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db_path = Path(db_path)
        self._repo = ExecutionRepository(self._db_path)

        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        self._btn_refresh = QPushButton("刷新")
        self._btn_refresh.clicked.connect(self._refresh)
        bar.addWidget(self._btn_refresh)
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
        root.addWidget(self._table)

        self._refresh()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        try:
            executions = self._repo.list_recent(200)
        except OSError as exc:
            _logger.exception("Failed to list executions")
            self._table.setRowCount(1)
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
            tooltip = "\n".join(tip_lines)

            for col_i, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if col_i == 0 and file_name:
                    item.setToolTip(f"{tooltip}\nsource_file: {file_name}")
                else:
                    item.setToolTip(tooltip)
                self._table.setItem(row_i, col_i, item)
