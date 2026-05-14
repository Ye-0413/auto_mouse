from __future__ import annotations

from typing import Any, Callable

from rpa_assistant.app.automation import desktop
from rpa_assistant.app.automation.browser_pw import PlaywrightSession
from rpa_assistant.app.automation.result import ActionResult
from rpa_assistant.app.core.condition_engine import evaluate_condition
from rpa_assistant.app.core.variable_engine import substitute_structure

LogFn = Callable[[str], None]
AfterStepFn = Callable[[int, dict[str, Any], ActionResult], None]


class FlowRunner:
    """Execute flow steps with variable substitution and ``if`` branches."""

    def __init__(
        self,
        log: LogFn | None = None,
        *,
        browser_cdp_url: str | None = None,
    ) -> None:
        self._log = log or (lambda _s: None)
        self._step_seq = 0
        self._browser_cdp_url = (browser_cdp_url or "").strip() or None
        self._pw_session: PlaywrightSession | None = None

    def _next_after(
        self,
        after_step: AfterStepFn | None,
        step: dict[str, Any],
        res: ActionResult,
    ) -> None:
        if after_step:
            i = self._step_seq
            self._step_seq += 1
            after_step(i, step, res)

    def run(
        self,
        steps: list[dict[str, Any]],
        variables: dict[str, Any],
        *,
        stop_on_error: bool = True,
        after_step: AfterStepFn | None = None,
    ) -> tuple[bool, str]:
        self._step_seq = 0
        self._pw_session = None
        try:
            return self._run_block(
                steps,
                variables,
                stop_on_error=stop_on_error,
                after_step=after_step,
            )
        finally:
            if self._pw_session is not None:
                self._pw_session.close()
                self._pw_session = None

    def _run_block(
        self,
        steps: list[dict[str, Any]],
        variables: dict[str, Any],
        *,
        stop_on_error: bool,
        after_step: AfterStepFn | None,
    ) -> tuple[bool, str]:
        last_err = ""
        for step in steps:
            st = step.get("type")
            if st == "note":
                self._log(f"[{self._step_seq + 1}] 备注步骤，跳过")
                self._next_after(after_step, step, ActionResult(True))
                continue

            if st == "if":
                raw_params = step.get("params")
                if not isinstance(raw_params, dict) and isinstance(
                    step.get("value"),
                    dict,
                ):
                    raw_params = step["value"]
                elif not isinstance(raw_params, dict):
                    raw_params = {}
                try:
                    cond_raw = raw_params.get("condition")
                    if cond_raw is None:
                        raise ValueError("if 步骤缺少 params.condition")
                    cond_sub = substitute_structure(
                        cond_raw,
                        variables,
                        strict=False,
                    )
                    if not isinstance(cond_sub, dict):
                        raise ValueError("condition 替换后必须是对象")
                    branch_true = evaluate_condition(cond_sub)
                except (ValueError, KeyError) as exc:
                    err = f"条件无效: {exc}"
                    self._log(err)
                    last_err = err
                    self._next_after(
                        after_step,
                        step,
                        ActionResult(False, err),
                    )
                    if stop_on_error:
                        return False, last_err
                    continue

                then_steps = raw_params.get("then")
                else_steps = raw_params.get("else")
                if then_steps is None:
                    then_steps = []
                if else_steps is None:
                    else_steps = []
                if not isinstance(then_steps, list) or not isinstance(
                    else_steps,
                    list,
                ):
                    err = "if: then / else 必须是数组"
                    self._log(err)
                    last_err = err
                    self._next_after(
                        after_step,
                        step,
                        ActionResult(False, err),
                    )
                    if stop_on_error:
                        return False, last_err
                    continue

                tag = "then" if branch_true else "else"
                self._log(
                    f"[{self._step_seq + 1}] 条件分支 → {tag}（真值: {branch_true}）",
                )
                self._next_after(
                    after_step,
                    step,
                    ActionResult(True, f"条件为真" if branch_true else "条件为假"),
                )
                sub = then_steps if branch_true else else_steps
                sub_ok, sub_err = self._run_block(
                    sub,
                    variables,
                    stop_on_error=stop_on_error,
                    after_step=after_step,
                )
                if not sub_ok:
                    return False, sub_err
                continue

            raw_params = step.get("params")
            if not isinstance(raw_params, dict) and isinstance(
                step.get("value"),
                dict,
            ):
                raw_params = step["value"]
            elif not isinstance(raw_params, dict):
                raw_params = {}
            try:
                params = substitute_structure(raw_params, variables, strict=False)
            except KeyError as exc:
                err = f"变量未定义: {exc}"
                self._log(err)
                last_err = err
                self._next_after(after_step, step, ActionResult(False, err))
                if stop_on_error:
                    return False, last_err
                continue
            self._log(f"[{self._step_seq + 1}] 执行 {st} …")
            stt = str(st)
            if stt.startswith("pw_"):
                if self._pw_session is None:
                    self._pw_session = PlaywrightSession()
                res = self._pw_session.run_step(
                    stt,
                    params,
                    default_cdp_url=self._browser_cdp_url,
                )
            else:
                res = desktop.run_step(stt, params)
            self._next_after(after_step, step, res)
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
