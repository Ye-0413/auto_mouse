from rpa_assistant.app.ui.flow.presentation import step_type_label, summarize_step


def test_step_type_label() -> None:
    assert step_type_label("wait") == "等待"


def test_summarize_wait() -> None:
    s = {"type": "wait", "params": {"ms": 1500}}
    assert "1500" in summarize_step(s)
