"""Desktop event recording (optional ``pynput`` dependency)."""

from __future__ import annotations

from rpa_assistant.app.recording.step_builders import (
    new_click_mouse_step,
    new_hotkey_step,
    new_input_text_step,
)

__all__ = [
    "new_click_mouse_step",
    "new_hotkey_step",
    "new_input_text_step",
]
