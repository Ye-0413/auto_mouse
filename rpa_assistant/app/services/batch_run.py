from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from rpa_assistant.app.automation.desktop import capture_screen_to_file
from rpa_assistant.app.automation.result import ActionResult
from rpa_assistant.app.core.runner import FlowRunner
from rpa_assistant.app.excel.mapper import row_to_variables
from rpa_assistant.app.models.common import ExecutionStatus, StepRunStatus
from rpa_assistant.app.models.execution import ExecutionRecord, StepRunRecord
from rpa_assistant.app.storage.execution_repo import ExecutionRepository

LogFn = Callable[[str], None]
CancelRequestedFn = Callable[[], bool]
PauseRequestedFn = Callable[[], bool]


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
    screenshot_on_error: bool = False,
    screenshots_dir: Path | None = None,
    cancel_requested: CancelRequestedFn | None = None,
    pause_requested: PauseRequestedFn | None = None,
    browser_cdp_url: str | None = None,
    ui_preview_indices: list[int] | None = None,
    on_row_started: Callable[[int | None], None] | None = None,
    on_row_finished: Callable[[int | None, str, bool], None] | None = None,
) -> tuple[int, int, bool, str]:
    """
    Run the same flow for each data row.

    Returns (success_count, fail_count, cancelled, batch_id).

    ui_preview_indices, when set, must align 1:1 with data_rows (Preview table row index).

    Pause: when pause_requested returns True, spin until it becomes False or cancel_requested.
    """
    batch_id = str(uuid.uuid4())
    ok_c = 0
    fail_c = 0
    runner = FlowRunner(log, browser_cdp_url=browser_cdp_url)
    for row_pos, row in enumerate(data_rows, start=1):
        while pause_requested is not None and pause_requested():
            if cancel_requested is not None and cancel_requested():
                log("── 用户已取消（在暂停状态中），停止后续数据行。")
                return ok_c, fail_c, True, batch_id
            time.sleep(0.05)

        if cancel_requested is not None and cancel_requested():
            log("── 用户已取消，停止后续数据行。")
            return ok_c, fail_c, True, batch_id

        preview_ix: int | None = None
        if ui_preview_indices is not None and row_pos - 1 < len(ui_preview_indices):
            preview_ix = ui_preview_indices[row_pos - 1]

        if on_row_started is not None:
            on_row_started(preview_ix)

        vars_dict = row_to_variables(headers, row, variable_map)
        log(f"── 数据行 {row_pos}，变量: {vars_dict!r}")
        ex = ExecutionRecord(
            id="",
            status=ExecutionStatus.RUNNING,
            batch_id=batch_id,
            flow_id=flow_id,
            config_id=config_id,
            variables=dict(vars_dict),
            source_file=str(excel_path) if excel_path else None,
            source_sheet=sheet_name,
            source_row_index=row_pos,
            started_at=_now(),
        )
        eid = exec_repo.create_execution(ex)

        def after_step(
            i: int,
            step: dict[str, Any],
            res: ActionResult,
        ) -> None:
            st_name = str(step.get("type", "") or "")
            strat = "playwright" if st_name.startswith("pw_") else "desktop"
            out = {"ok": res.ok, "message": res.message}
            if res.value is not None:
                out["value"] = res.value
            sr = StepRunRecord(
                id="",
                execution_id=eid,
                status=StepRunStatus.SUCCESS if res.ok else StepRunStatus.FAILED,
                step_id=str(step.get("id", "")),
                order_index=i,
                step_type=str(step.get("type", "")),
                strategy_used=strat,
                input_data=step,
                output_data=out,
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
            ended.variables = dict(vars_dict)
            if not all_ok and screenshot_on_error and screenshots_dir is not None:
                ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                shot_name = f"{eid[:8]}_row{row_pos}_{ts}.png"
                shot_path = screenshots_dir / shot_name
                cap_res = capture_screen_to_file(shot_path)
                if cap_res.ok:
                    ended.screenshot_path = str(shot_path)
                    log(f"已保存错误截图：{ended.screenshot_path}")
                else:
                    log(f"错误截图未保存：{cap_res.message}")
            elif all_ok:
                ended.screenshot_path = None
            exec_repo.update(ended)

        summary = "成功" if all_ok else "失败"
        if on_row_finished is not None:
            on_row_finished(preview_ix, summary, all_ok)

        if all_ok:
            ok_c += 1
        else:
            fail_c += 1
    return ok_c, fail_c, False, batch_id
