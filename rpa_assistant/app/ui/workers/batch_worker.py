from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal

from rpa_assistant.app.services.batch_run import run_rows_sync
from rpa_assistant.app.storage.execution_repo import ExecutionRepository


class BatchRunWorker(QThread):
    """Runs batch execution in a background thread."""

    log_line = Signal(str)
    finished_counts = Signal(int, int, str)

    def __init__(
        self,
        db_path: Path,
        *,
        steps: list[dict[str, Any]],
        headers: list[str],
        data_rows: list[list[str]],
        variable_map: dict[str, str],
        config_id: str | None,
        flow_id: str | None,
        excel_path: Path | None,
        sheet_name: str | None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._steps = steps
        self._headers = headers
        self._data_rows = data_rows
        self._variable_map = variable_map
        self._config_id = config_id
        self._flow_id = flow_id
        self._excel_path = excel_path
        self._sheet_name = sheet_name

    def run(self) -> None:
        rep = ExecutionRepository(self._db_path)

        def log(msg: str) -> None:
            self.log_line.emit(msg)

        try:
            ok, fail = run_rows_sync(
                steps=self._steps,
                headers=self._headers,
                data_rows=self._data_rows,
                variable_map=self._variable_map,
                config_id=self._config_id,
                flow_id=self._flow_id,
                excel_path=self._excel_path,
                sheet_name=self._sheet_name,
                exec_repo=rep,
                log=log,
            )
            self.finished_counts.emit(ok, fail, "")
        except Exception as exc:
            self.finished_counts.emit(0, 0, str(exc))
