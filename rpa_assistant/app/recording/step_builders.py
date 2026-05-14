"""Pure helpers to build FlowEditor-compatible step dicts (testable without pynput)."""

from __future__ import annotations

import uuid
from typing import Any


def new_click_mouse_step(x: int, y: int, *, button: str = "left") -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "type": "click_mouse",
        "params": {"x": int(x), "y": int(y), "button": button},
    }


def new_input_text_step(text: str) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "type": "input_text",
        "params": {"text": text},
    }


def new_hotkey_step(keys: str) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "type": "hotkey",
        "params": {"keys": keys.strip()},
    }
