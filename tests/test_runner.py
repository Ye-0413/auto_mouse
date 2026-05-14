from __future__ import annotations

from unittest.mock import MagicMock, patch

from rpa_assistant.app.automation.result import ActionResult
from rpa_assistant.app.core.runner import FlowRunner


@patch("rpa_assistant.app.core.runner.desktop.run_step")
def test_flow_runner_wait_ok(mock_step) -> None:
    mock_step.return_value = ActionResult(True)
    runner = FlowRunner()
    ok, err = runner.run([{"type": "wait", "params": {"ms": 1}}], {})
    assert ok
    assert err == ""
    mock_step.assert_called_once()


@patch("rpa_assistant.app.core.runner.desktop.run_step")
def test_flow_runner_note_skips_desktop(mock_step) -> None:
    runner = FlowRunner()
    ok, err = runner.run([{"type": "note", "params": {}}], {})
    assert ok
    assert err == ""
    mock_step.assert_not_called()


@patch("rpa_assistant.app.core.runner.desktop.run_step")
def test_flow_runner_after_step(mock_step) -> None:
    mock_step.return_value = ActionResult(True)
    seen: list[tuple[int, str | None, bool]] = []

    def after_step(i: int, step: dict, res: ActionResult) -> None:
        seen.append((i, step.get("type"), res.ok))

    runner = FlowRunner()
    ok, _ = runner.run(
        [{"type": "wait", "params": {"ms": 0}}],
        {},
        after_step=after_step,
    )
    assert ok
    assert seen == [(0, "wait", True)]


@patch("rpa_assistant.app.core.runner.desktop.run_step")
def test_flow_runner_stops_on_first_failure(mock_step) -> None:
    mock_step.return_value = ActionResult(False, "step failed")

    runner = FlowRunner()
    ok, err = runner.run(
        [
            {"type": "wait", "params": {"ms": 1}},
            {"type": "wait", "params": {"ms": 2}},
        ],
        {},
    )
    assert not ok
    assert "step failed" in err
    assert mock_step.call_count == 1


@patch("rpa_assistant.app.core.runner.desktop.run_step")
def test_flow_runner_substitute_params(mock_step) -> None:
    mock_step.return_value = ActionResult(True)

    runner = FlowRunner()
    ok, _ = runner.run(
        [{"type": "input_text", "params": {"text": "Hello ${name}"}}],
        {"name": "World"},
    )
    assert ok
    mock_step.assert_called_once()
    call = mock_step.call_args[0]
    assert call[0] == "input_text"
    assert call[1]["text"] == "Hello World"


@patch("rpa_assistant.app.core.runner.desktop.run_step")
def test_flow_runner_accepts_value_alias(mock_step) -> None:
    mock_step.return_value = ActionResult(True)
    runner = FlowRunner()
    ok, _ = runner.run(
        [{"type": "wait", "value": {"ms": 0}}],
        {},
    )
    assert ok
    mock_step.assert_called_once()
    assert mock_step.call_args[0][1] == {"ms": 0}


@patch("rpa_assistant.app.core.runner.desktop.run_step")
def test_flow_runner_if_then_branch(mock_step) -> None:
    mock_step.return_value = ActionResult(True)
    steps = [
        {
            "type": "if",
            "params": {
                "condition": {"op": "equals", "left": "${x}", "right": "1"},
                "then": [{"type": "wait", "params": {"ms": 10}}],
                "else": [{"type": "wait", "params": {"ms": 99}}],
            },
        },
    ]
    runner = FlowRunner()
    ok, err = runner.run(steps, {"x": "1"})
    assert ok and err == ""
    mock_step.assert_called_once()
    assert mock_step.call_args[0][1]["ms"] == 10


@patch("rpa_assistant.app.core.runner.desktop.run_step")
def test_flow_runner_if_else_branch(mock_step) -> None:
    mock_step.return_value = ActionResult(True)
    steps = [
        {
            "type": "if",
            "params": {
                "condition": {"op": "equals", "left": "${x}", "right": "1"},
                "then": [{"type": "wait", "params": {"ms": 10}}],
                "else": [{"type": "wait", "params": {"ms": 20}}],
            },
        },
    ]
    runner = FlowRunner()
    ok, err = runner.run(steps, {"x": "2"})
    assert ok and err == ""
    mock_step.assert_called_once()
    assert mock_step.call_args[0][1]["ms"] == 20


def test_flow_runner_set_variable_writes() -> None:
    runner = FlowRunner()
    v: dict[str, str | int] = {"a": "9"}
    ok, err = runner.run(
        [{"type": "set_variable", "params": {"name": "row_tag", "value": "batch-${a}"}}],
        v,
    )
    assert ok and err == ""
    assert v["row_tag"] == "batch-9"


@patch("rpa_assistant.app.core.runner.PlaywrightSession")
def test_flow_runner_pw_inner_text_assigns_variable(mock_sess_cls: MagicMock) -> None:
    inst = MagicMock()
    mock_sess_cls.return_value = inst
    inst.run_step.return_value = ActionResult(True, "", value="  低压居民合同  ")
    runner = FlowRunner(browser_cdp_url="http://127.0.0.1:1")
    v: dict[str, str | int | None] = {"a": 1}
    ok, err = runner.run(
        [
            {
                "type": "pw_inner_text",
                "params": {
                    "into": "ctype",
                    "text": "",
                    "css": "tbody tr",
                    "nth": 0,
                    "exact": False,
                    "timeout_ms": 999,
                    "cdp_url": "",
                },
            },
        ],
        v,
        after_step=lambda *_a: None,
    )
    assert ok and err == ""
    assert v["ctype"] == "低压居民合同"
    assert v["a"] == 1
