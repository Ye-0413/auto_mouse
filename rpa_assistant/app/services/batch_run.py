from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from rpa_assistant.app.automation.result import ActionResult
from rpa_assistant.app.core.runner import FlowRunner
from rpa_assistant.app.excel.mapper import row_to_variables
from rpa_assistant.app.models.common import ExecutionStatus, StepRunStatus
from rpa_assistant.app.models.execution import ExecutionRecord, StepRunRecord
from rpa_assistant.app.storage.execution_repo import ExecutionRepository

LogFn = Callable[[str], None]


def _now() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds")


def run_rows_sync(
    *,
    steps: list[dict[str, Any]],
    headers: list[str],
    data_rows: list[list[str]],
    variable_map: dict[str, str],
    config_id: str | None,
    flow_id: str | None,
    excel_path: Path | None,
    sheet_name: str | None,
    exec_repo: ExecutionRepository,
    log: LogFn,
) -> tuple[int, int]:
    """
    Run the same flow for each data row. Returns (success_count, fail_count).
    """
    batch_id = str(uuid.uuid4())
    ok_c = 0
    fail_c = 0
    runner = FlowRunner(log)
    for row_index, row in enumerate(data_rows, start=1):
        vars_dict = row_to_variables(headers, row, variable_map)
        log(f"── 数据行 {row_index}，变量: {vars_dict!r}")
        ex = ExecutionRecord(
            id="",
            status=ExecutionStatus.RUNNING,
            batch_id=batch_id,
            flow_id=flow_id,
            config_id=config_id,
            variables=vars_dict,
            source_file=str(excel_path) if excel_path else None,
            source_sheet=sheet_name,
            source_row_index=row_index,
            started_at=_now(),
        )
        eid = exec_repo.create_execution(ex)

        def after_step(
            i: int,
            step: dict[str, Any],
            res: ActionResult,
        ) -> None:
            sr = StepRunRecord(
                id="",
                execution_id=eid,
                status=StepRunStatus.SUCCESS if res.ok else StepRunStatus.FAILED,
                step_id=str(step.get("id", "")),
                order_index=i,
                step_type=str(step.get("type", "")),
                strategy_used="desktop",
                input_data=step,
                output_data={"ok": res.ok, "message": res.message},
                error_message=None if res.ok else res.message,
                started_at=_now(),
                ended_at=_now(),
            )
            exec_repo.add_step_run(sr)

        all_ok, err = runner.run(
            steps,
            vars_dict,
            after_step=after_step,
        )
        ended = exec_repo.get(eid)
        if ended:
            ended.status = ExecutionStatus.SUCCESS if all_ok else ExecutionStatus.FAILED
            ended.error_message = None if all_ok else err
            ended.ended_at = _now()
            exec_repo.update(ended)
        if all_ok:
            ok_c += 1
        else:
            fail_c += 1
    return ok_c, fail_c
