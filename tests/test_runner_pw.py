from __future__ import annotations

from unittest.mock import MagicMock, patch

from rpa_assistant.app.automation.result import ActionResult
from rpa_assistant.app.core.runner import FlowRunner


@patch("rpa_assistant.app.core.runner.PlaywrightSession")
def test_pw_step_dispatches_to_session(mock_sess_cls) -> None:
    inst = MagicMock()
    inst.run_step.return_value = ActionResult(True)
    mock_sess_cls.return_value = inst

    runner = FlowRunner(browser_cdp_url="http://127.0.0.1:9222")
    ok, err = runner.run(
        [{"type": "pw_goto", "params": {"url": "https://example.com"}}],
        {},
    )
    assert ok and err == ""
    inst.run_step.assert_called_once()
    assert inst.run_step.call_args[0][0] == "pw_goto"
    inst.close.assert_called_once()
