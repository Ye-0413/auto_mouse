from __future__ import annotations

from typing import Any, Callable

from rpa_assistant.app.automation import desktop
from rpa_assistant.app.automation.result import ActionResult
from rpa_assistant.app.core.variable_engine import substitute_structure

LogFn = Callable[[str], None]
AfterStepFn = Callable[[int, dict[str, Any], ActionResult], None]


class FlowRunner:
    """Execute flow steps with variable substitution."""

    def __init__(self, log: LogFn | None = None) -> None:
        self._log = log or (lambda _s: None)

    def run(
        self,
        steps: list[dict[str, Any]],
        variables: dict[str, Any],
        *,
        stop_on_error: bool = True,
        after_step: AfterStepFn | None = None,
    ) -> tuple[bool, str]:
        last_err = ""
        for i, step in enumerate(steps):
            st = step.get("type")
            if st == "note":
                self._log(f"[{i + 1}] 备注步骤，跳过")
                if after_step:
                    after_step(i, step, ActionResult(True))
                continue
            raw_params = step.get("params")
            if not isinstance(raw_params, dict) and isinstance(step.get("value"), dict):
                raw_params = step["value"]
            elif not isinstance(raw_params, dict):
                raw_params = {}
            try:
                params = substitute_structure(raw_params, variables, strict=False)
            except KeyError as exc:
                err = f"变量未定义: {exc}"
                self._log(err)
                last_err = err
                if after_step:
                    after_step(i, step, ActionResult(False, err))
                if stop_on_error:
                    return False, last_err
                continue
            self._log(f"[{i + 1}] 执行 {st} …")
            res = desktop.run_step(str(st), params)
            if after_step:
                after_step(i, step, res)
            if not res.ok:
                last_err = res.message or "步骤失败"
                self._log(f"  ✗ {last_err}")
                if stop_on_error:
                    return False, last_err
            else:
                if res.message:
                    self._log(f"  ⚠ {res.message}")
                self._log("  ✓ 完成")
        return last_err == "", last_err
