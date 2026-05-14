from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from rpa_assistant.app.automation.result import ActionResult
from rpa_assistant.app.models.common import ExecutionStatus
from rpa_assistant.app.services.single_flow_run import run_single_flow_sync
from rpa_assistant.app.storage.database import init_database
from rpa_assistant.app.storage.execution_repo import ExecutionRepository


@patch("rpa_assistant.app.core.runner.desktop.run_step")
def test_run_single_flow_sync_ok(mock_step, tmp_path: Path) -> None:
    mock_step.return_value = ActionResult(True)
    db = tmp_path / "s.sqlite3"
    init_database(db)
    repo = ExecutionRepository(db)

    steps = [{"id": "x", "type": "wait", "params": {"ms": 1}}]
    ok, err, eid = run_single_flow_sync(
        steps=steps,
        flow_id=None,
        config_id=None,
        variables={"a": "1"},
        exec_repo=repo,
        log=lambda m: None,
    )

    assert ok
    assert err == ""
    assert eid
    ex = repo.get(eid)
    assert ex is not None
    assert ex.status == ExecutionStatus.SUCCESS
    sr = repo.list_step_runs(eid)
    assert len(sr) >= 1


@patch("rpa_assistant.app.core.runner.desktop.run_step")
def test_run_single_flow_sync_fail(mock_step, tmp_path: Path) -> None:
    mock_step.return_value = ActionResult(False, message="nope")
    db = tmp_path / "f.sqlite3"
    init_database(db)
    repo = ExecutionRepository(db)

    with patch(
        "rpa_assistant.app.services.single_flow_run.capture_screen_to_file",
        return_value=ActionResult(True),
    ):
        ok, err, eid = run_single_flow_sync(
            steps=[{"id": "z", "type": "wait", "params": {"ms": 1}}],
            flow_id=None,
            config_id=None,
            variables=None,
            exec_repo=repo,
            log=lambda m: None,
            screenshot_on_error=True,
            screenshots_dir=tmp_path,
        )

    assert not ok
    assert eid
    ex = repo.get(eid)
    assert ex is not None
    assert ex.status == ExecutionStatus.FAILED
