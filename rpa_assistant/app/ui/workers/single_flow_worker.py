from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal

from rpa_assistant.app.services.single_flow_run import run_single_flow_sync
from rpa_assistant.app.storage.execution_repo import ExecutionRepository


class SingleFlowRunWorker(QThread):
    log_line = Signal(str)
    finished_run = Signal(bool, str, str)

    def __init__(
        self,
        db_path: Path,
        *,
        steps: list[dict[str, Any]],
        flow_id: str | None,
        config_id: str | None,
        variables: dict[str, Any] | None,
        screenshot_on_error: bool = False,
        screenshots_dir: Path | None = None,
        browser_cdp_url: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._steps = steps
        self._flow_id = flow_id
        self._config_id = config_id
        self._variables = variables
        self._screenshot_on_error = screenshot_on_error
        self._screenshots_dir = screenshots_dir
        self._browser_cdp_url = browser_cdp_url

    def run(self) -> None:
        rep = ExecutionRepository(self._db_path)

        def log(msg: str) -> None:
            self.log_line.emit(msg)

        try:
            ok, err, eid = run_single_flow_sync(
                steps=list(self._steps),
                flow_id=self._flow_id,
                config_id=self._config_id,
                variables=self._variables,
                exec_repo=rep,
                log=log,
                screenshot_on_error=self._screenshot_on_error,
                screenshots_dir=self._screenshots_dir,
                browser_cdp_url=self._browser_cdp_url,
            )
            self.finished_run.emit(ok, err, eid)
        except Exception as exc:
            self.finished_run.emit(False, str(exc), "")
