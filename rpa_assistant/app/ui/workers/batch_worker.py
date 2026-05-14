from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal

from rpa_assistant.app.excel.reader import load_all_data_rows
from rpa_assistant.app.services.batch_run import run_rows_sync
from rpa_assistant.app.storage.execution_repo import ExecutionRepository


class BatchRunWorker(QThread):
    """Runs batch execution in a background thread."""

    log_line = Signal(str)
    finished_counts = Signal(int, int, str, bool, str)
    row_started_signal = Signal(object)
    row_finished_signal = Signal(object, str, bool)

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
        header_row_1based: int = 1,
        load_full_sheet: bool = False,
        screenshot_on_error: bool = False,
        screenshots_dir: Path | None = None,
        browser_cdp_url: str | None = None,
        ui_preview_indices: list[int] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._cancel = threading.Event()
        self._pause = threading.Event()
        self._steps = steps
        self._headers = headers
        self._data_rows = data_rows
        self._variable_map = variable_map
        self._config_id = config_id
        self._flow_id = flow_id
        self._excel_path = excel_path
        self._sheet_name = sheet_name
        self._header_row_1based = header_row_1based
        self._load_full_sheet = load_full_sheet
        self._screenshot_on_error = screenshot_on_error
        self._screenshots_dir = screenshots_dir
        self._browser_cdp_url = browser_cdp_url
        self._ui_preview_indices = ui_preview_indices

    def request_cancel(self) -> None:
        self._cancel.set()

    def request_pause(self) -> None:
        """Pause before starting the next data row."""
        self._pause.set()

    def request_resume(self) -> None:
        self._pause.clear()

    def is_pause_flag_set(self) -> bool:
        return self._pause.is_set()

    def run(self) -> None:
        rep = ExecutionRepository(self._db_path)

        def log(msg: str) -> None:
            self.log_line.emit(msg)

        def on_row_started(preview_ix: int | None) -> None:
            self.row_started_signal.emit(preview_ix)

        def on_row_finished(preview_ix: int | None, label: str, ok_row: bool) -> None:
            self.row_finished_signal.emit(preview_ix, label, ok_row)

        self._cancel.clear()
        try:
            headers = self._headers
            data_rows = self._data_rows
            ui_ix = None if self._load_full_sheet else self._ui_preview_indices
            if self._load_full_sheet:
                if not self._excel_path or not self._sheet_name:
                    raise ValueError("整表执行需要已选择的 Excel 文件与工作表")
                log(
                    f"正在从工作簿读取全部数据行（表头在第 {self._header_row_1based} 行）…",
                )
                headers, data_rows = load_all_data_rows(
                    self._excel_path,
                    self._sheet_name,
                    header_row_1based=self._header_row_1based,
                )
                log(f"已加载 {len(data_rows)} 行（含可能的空行）。")

            pause_fn = self._pause.is_set
            ok, fail, cancelled, batch_id = run_rows_sync(
                steps=self._steps,
                headers=headers,
                data_rows=data_rows,
                variable_map=self._variable_map,
                config_id=self._config_id,
                flow_id=self._flow_id,
                excel_path=self._excel_path,
                sheet_name=self._sheet_name,
                exec_repo=rep,
                log=log,
                screenshot_on_error=self._screenshot_on_error,
                screenshots_dir=self._screenshots_dir,
                cancel_requested=self._cancel.is_set,
                pause_requested=pause_fn,
                browser_cdp_url=self._browser_cdp_url,
                ui_preview_indices=ui_ix,
                on_row_started=on_row_started,
                on_row_finished=on_row_finished,
            )
            self.finished_counts.emit(ok, fail, "", cancelled, batch_id)
        except Exception as exc:
            self.finished_counts.emit(0, 0, str(exc), False, "")
