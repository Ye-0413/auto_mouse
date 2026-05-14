from __future__ import annotations

import pytest

pytest.importorskip("pynput")

from pynput.keyboard import Key  # noqa: E402

from rpa_assistant.app.recording.key_mapping import build_hotkey_string  # noqa: E402


class _KeyChar:
    """Tiny stand-in for ``KeyCode`` with a printable ``char``."""

    def __init__(self, ch: str) -> None:
        self.char = ch


def test_build_hotkey_string_orders_modifiers() -> None:
    hk = build_hotkey_string({"ctrl", "shift"}, _KeyChar("v"))
    assert hk == "ctrl+shift+v"


def test_build_hotkey_special_key() -> None:
    hk = build_hotkey_string(set(), Key.tab)
    assert hk == "tab"


def test_build_hotkey_uppercase_letter_normalized() -> None:
    hk = build_hotkey_string({"ctrl"}, _KeyChar("V"))
    assert hk == "ctrl+v"
