"""Map ``pynput`` keys to runner-facing hotkey strings (no Qt dependency)."""

from __future__ import annotations

from typing import Any


def mod_token(key: Any) -> str | None:
    try:
        from pynput.keyboard import Key
    except ImportError:
        return None
    if key in (Key.ctrl_l, Key.ctrl_r):
        return "ctrl"
    if key in (Key.alt_l, Key.alt_r, Key.alt):
        return "alt"
    if key in (Key.shift_l, Key.shift_r, Key.shift):
        return "shift"
    if key in (Key.cmd_l, Key.cmd_r, Key.cmd):
        return "cmd"
    return None


def special_hotkey_token(key: Any) -> str | None:
    """Single-key names when emitting a standalone ``hotkey`` step (no modifiers)."""
    try:
        from pynput.keyboard import Key
    except ImportError:
        return None
    mapping: dict[Any, str] = {
        Key.tab: "tab",
        Key.delete: "delete",
        Key.esc: "escape",
        Key.up: "up",
        Key.down: "down",
        Key.left: "left",
        Key.right: "right",
        Key.home: "home",
        Key.end: "end",
        Key.page_up: "pageup",
        Key.page_down: "pagedown",
        Key.f1: "f1",
        Key.f2: "f2",
        Key.f3: "f3",
        Key.f4: "f4",
        Key.f5: "f5",
        Key.f6: "f6",
        Key.f7: "f7",
        Key.f8: "f8",
        Key.f9: "f9",
        Key.f10: "f10",
        Key.f11: "f11",
        Key.f12: "f12",
    }
    return mapping.get(key)


def _vk_hotkey_name(key: Any) -> str | None:
    tok = special_hotkey_token(key)
    if tok:
        return tok
    ch = getattr(key, "char", None)
    if ch:
        if ch.isalpha():
            return ch.lower()
        if ch.isdigit():
            return ch
        sym_map = {
            "`": "`",
            "-": "-",
            "=": "=",
            "[": "[",
            "]": "]",
            "\\": "\\",
            ";": ";",
            "'": "'",
            ",": ",",
            ".": ".",
            "/": "/",
        }
        return sym_map.get(ch, ch if len(ch) == 1 else None)
    try:
        from pynput.keyboard import Key
    except ImportError:
        return None
    if key == Key.print_screen:
        return "printscreen"
    return None


def build_hotkey_string(mods: set[str], key: Any) -> str | None:
    """Human-readable combo matching ``desktop._hotkey`` parsing (e.g. ctrl+shift+t)."""
    name = _vk_hotkey_name(key)
    if not name:
        return None
    order: list[str] = []
    if "ctrl" in mods:
        order.append("ctrl")
    if "alt" in mods:
        order.append("alt")
    if "shift" in mods:
        order.append("shift")
    if "cmd" in mods:
        order.append("cmd")
    order.append(name)
    return "+".join(order)
