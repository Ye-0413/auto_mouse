from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from rpa_assistant.app.automation.result import ActionResult
from rpa_assistant.app.services.batch_run import run_rows_sync
from rpa_assistant.app.storage.database import init_database
from rpa_assistant.app.storage.execution_repo import ExecutionRepository


def test_run_rows_respects_cancel_before_second_row(
    tmp_path: Path,
) -> None:
    db = tmp_path / "c.sqlite3"
    init_database(db)
    repo = ExecutionRepository(db)
    state = {"n": 0}

    def should_cancel() -> bool:
        state["n"] += 1
        return state["n"] >= 2

    with patch(
        "rpa_assistant.app.core.runner.desktop.run_step",
        return_value=ActionResult(True),
    ):
        ok, fail, cancelled = run_rows_sync(
            steps=[{"type": "wait", "params": {"ms": 0}}],
            headers=["A"],
            data_rows=[["1"], ["2"]],
            variable_map={},
            config_id=None,
            flow_id=None,
            excel_path=None,
            sheet_name=None,
            exec_repo=repo,
            log=lambda _m: None,
            cancel_requested=should_cancel,
        )
    assert cancelled
    assert ok == 1 and fail == 0
    assert len(repo.list_recent(10)) == 1
