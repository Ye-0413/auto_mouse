from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from rpa_assistant.app.automation.result import ActionResult
from rpa_assistant.app.services.batch_run import run_rows_sync
from rpa_assistant.app.storage.database import init_database
from rpa_assistant.app.storage.execution_repo import ExecutionRepository


def test_run_rows_sync_saves_screenshot_on_failure(
    tmp_path: Path,
) -> None:
    db = tmp_path / "t.sqlite3"
    init_database(db)
    repo = ExecutionRepository(db)
    shots = tmp_path / "shots"
    steps = [{"type": "wait", "params": {"ms": 0}}]

    with (
        patch(
            "rpa_assistant.app.core.runner.desktop.run_step",
            return_value=ActionResult(False, "boom"),
        ),
        patch(
            "rpa_assistant.app.services.batch_run.capture_screen_to_file",
            return_value=ActionResult(True),
        ) as mock_cap,
    ):
        ok, fail, cancelled = run_rows_sync(
            steps=steps,
            headers=["A"],
            data_rows=[["1"]],
            variable_map={},
            config_id=None,
            flow_id=None,
            excel_path=None,
            sheet_name=None,
            exec_repo=repo,
            log=lambda _m: None,
            screenshot_on_error=True,
            screenshots_dir=shots,
        )
    assert ok == 0 and fail == 1 and not cancelled
    mock_cap.assert_called_once()
    recent = repo.list_recent(5)
    assert len(recent) == 1
    assert recent[0].screenshot_path is not None
    assert str(shots) in recent[0].screenshot_path


def test_run_rows_sync_skips_screenshot_when_disabled(
    tmp_path: Path,
) -> None:
    db = tmp_path / "u.sqlite3"
    init_database(db)
    repo = ExecutionRepository(db)
    shots = tmp_path / "shots2"

    with (
        patch(
            "rpa_assistant.app.core.runner.desktop.run_step",
            return_value=ActionResult(False, "boom"),
        ),
        patch(
            "rpa_assistant.app.services.batch_run.capture_screen_to_file",
            return_value=ActionResult(True),
        ) as mock_cap,
    ):
        ok, fail, cancelled = run_rows_sync(
            steps=[{"type": "wait", "params": {"ms": 0}}],
            headers=["A"],
            data_rows=[["1"]],
            variable_map={},
            config_id=None,
            flow_id=None,
            excel_path=None,
            sheet_name=None,
            exec_repo=repo,
            log=lambda _m: None,
            screenshot_on_error=False,
            screenshots_dir=shots,
        )
    assert ok == 0 and fail == 1 and not cancelled
    mock_cap.assert_not_called()
