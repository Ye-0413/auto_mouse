"""Run one flow once with a fixed variable map (no Excel rows)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from rpa_assistant.app.automation.desktop import capture_screen_to_file
from rpa_assistant.app.automation.result import ActionResult
from rpa_assistant.app.core.runner import FlowRunner
from rpa_assistant.app.models.common import ExecutionStatus, StepRunStatus
from rpa_assistant.app.models.execution import ExecutionRecord, StepRunRecord
from rpa_assistant.app.storage.execution_repo import ExecutionRepository

LogFn = Callable[[str], None]


def _now() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds")


def run_single_flow_sync(
    *,
    steps: list[dict[str, Any]],
    flow_id: str | None,
    config_id: str | None,
    variables: dict[str, Any] | None,
    exec_repo: ExecutionRepository,
    log: LogFn,
    screenshot_on_error: bool = False,
    screenshots_dir: Path | None = None,
    browser_cdp_url: str | None = None,
) -> tuple[bool, str, str]:
    """
    Execute steps once. Writes one execution + step_runs.

    Returns (all_ok, error_message_or_empty, execution_id).
    """
    batch_id = str(uuid.uuid4())
    vars_dict = dict(variables or {})
    runner = FlowRunner(log, browser_cdp_url=browser_cdp_url)
    ex = ExecutionRecord(
        id="",
        status=ExecutionStatus.RUNNING,
        batch_id=batch_id,
        flow_id=flow_id,
        config_id=config_id,
        variables=dict(vars_dict),
        source_file=None,
        source_sheet=None,
        source_row_index=None,
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

    log(f"── 单次运行，变量: {vars_dict!r}")
    all_ok, err = runner.run(steps, vars_dict, after_step=after_step)
    ended = exec_repo.get(eid)
    if ended:
        ended.status = ExecutionStatus.SUCCESS if all_ok else ExecutionStatus.FAILED
        ended.error_message = None if all_ok else err
        ended.ended_at = _now()
        ended.variables = dict(vars_dict)
        if not all_ok and screenshot_on_error and screenshots_dir is not None:
            ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            shot_name = f"{eid[:8]}_single_{ts}.png"
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

    return all_ok, err or "", eid
