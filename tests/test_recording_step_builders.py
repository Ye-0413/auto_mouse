from __future__ import annotations

from rpa_assistant.app.recording.step_builders import (
    new_click_mouse_step,
    new_hotkey_step,
    new_input_text_step,
)


def test_new_click_mouse_step_shape() -> None:
    s = new_click_mouse_step(10, 20, button="left")
    assert s["type"] == "click_mouse"
    assert "id" in s and len(str(s["id"])) > 0
    assert s["params"] == {"x": 10, "y": 20, "button": "left"}


def test_new_input_text_step_shape() -> None:
    s = new_input_text_step("你好 ${name}")
    assert s["type"] == "input_text"
    assert s["params"]["text"] == "你好 ${name}"


def test_new_hotkey_step_shape() -> None:
    s = new_hotkey_step("ctrl+v")
    assert s["type"] == "hotkey"
    assert s["params"]["keys"] == "ctrl+v"
