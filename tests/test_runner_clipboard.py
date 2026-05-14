from __future__ import annotations

from unittest.mock import patch

from rpa_assistant.app.automation.result import ActionResult
from rpa_assistant.app.core.runner import FlowRunner


@patch("rpa_assistant.app.core.runner.desktop.read_clipboard_contents")
def test_read_clipboard_sets_variable(mock_read) -> None:
    mock_read.return_value = ActionResult(True, value="  hello  ")
    runner = FlowRunner()
    v: dict[str, str | int | None] = {}
    ok, err = runner.run(
        [{"type": "read_clipboard", "params": {"into": "x"}}],
        v,
    )
    assert ok and err == ""
    assert v["x"] == "hello"
    mock_read.assert_called_once()


@patch("rpa_assistant.app.core.runner.desktop.read_clipboard_contents")
def test_read_clipboard_no_strip(mock_read) -> None:
    mock_read.return_value = ActionResult(True, value="  hello  ")
    runner = FlowRunner()
    v: dict[str, str | int | None] = {}
    ok, err = runner.run(
        [{"type": "read_clipboard", "params": {"into": "x", "strip": False}}],
        v,
    )
    assert ok and err == ""
    assert v["x"] == "  hello  "


@patch("rpa_assistant.app.core.runner.desktop.run_step")
def test_clipboard_switch_runs_matching_branch(mock_step) -> None:
    mock_step.return_value = ActionResult(True)
    runner = FlowRunner()
    steps = [
        {
            "type": "clipboard_switch",
            "params": {
                "variable": "_clipboard",
                "rules": [
                    {
                        "contains_any": ["BBB"],
                        "steps": [{"type": "wait", "params": {"ms": 10}}],
                    },
                    {
                        "contains_any": ["低压"],
                        "steps": [{"type": "wait", "params": {"ms": 20}}],
                    },
                ],
            },
        },
        {"type": "wait", "params": {"ms": 999}},
    ]
    ok, err = runner.run(steps, {"_clipboard": "某低压供电合同"})
    assert ok and err == ""
    ms_list = [c.args[1]["ms"] for c in mock_step.call_args_list]
    assert ms_list == [20, 999]


@patch("rpa_assistant.app.core.runner.desktop.run_step")
def test_clipboard_switch_no_match_stops_run_silently(mock_step) -> None:
    runner = FlowRunner()
    steps = [
        {
            "type": "clipboard_switch",
            "params": {
                "variable": "_clipboard",
                "rules": [
                    {
                        "contains_any": ["Nomatch"],
                        "steps": [{"type": "wait", "params": {"ms": 1}}],
                    },
                ],
            },
        },
        {"type": "wait", "params": {"ms": 999}},
    ]
    ok, err = runner.run(steps, {"_clipboard": "plain"})
    assert ok and err == ""
    mock_step.assert_not_called()


@patch("rpa_assistant.app.core.runner.desktop.run_step")
def test_clipboard_switch_case_insensitive(mock_step) -> None:
    mock_step.return_value = ActionResult(True)
    runner = FlowRunner()
    steps = [
        {
            "type": "clipboard_switch",
            "params": {
                "variable": "_clipboard",
                "case_insensitive": True,
                "rules": [
                    {
                        "contains_any": ["AbC"],
                        "steps": [{"type": "wait", "params": {"ms": 33}}],
                    },
                ],
            },
        },
    ]
    ok, err = runner.run(steps, {"_clipboard": "xxabcyy"})
    assert ok and err == ""
    mock_step.assert_called_once()
    assert mock_step.call_args[0][1]["ms"] == 33


@patch("rpa_assistant.app.core.runner.desktop.run_step")
def test_clear_clipboard(mock_step) -> None:
    mock_step.return_value = ActionResult(True)
    runner = FlowRunner()
    ok, err = runner.run([{"type": "clear_clipboard", "params": {}}], {})
    assert ok and err == ""
    mock_step.assert_called_once()
    assert mock_step.call_args[0][0] == "clear_clipboard"
