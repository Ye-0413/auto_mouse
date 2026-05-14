"""Low-level desktop actions (keyboard, mouse, clipboard, window, browser)."""

from __future__ import annotations

import logging
import re
import sys
import time
import webbrowser
from typing import Any

import pyautogui
import pyperclip

from rpa_assistant.app.automation.result import ActionResult

_logger = logging.getLogger(__name__)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


def run_step(step_type: str, params: dict[str, Any]) -> ActionResult:
    """Dispatch one automation step after params are already resolved."""
    t = (step_type or "").strip()
    try:
        if t == "wait":
            ms = int(params.get("ms", 0))
            time.sleep(max(0, ms) / 1000.0)
            return ActionResult(True)
        if t == "input_text":
            text = str(params.get("text", ""))
            if not text:
                return ActionResult(False, "input_text: 文本为空")
            pyautogui.write(text, interval=0.02)
            return ActionResult(True)
        if t == "hotkey":
            keys = str(params.get("keys", "")).strip()
            if not keys:
                return ActionResult(False, "hotkey: 未填写组合键")
            return _hotkey(keys)
        if t == "activate_window":
            sub = str(params.get("title_contains", "")).strip()
            if not sub:
                return ActionResult(False, "activate_window: 未填写标题")
            return _activate_window(sub)
        if t == "open_url":
            url = str(params.get("url", "")).strip()
            if not url:
                return ActionResult(False, "open_url: 未填写网址")
            webbrowser.open(url, new=2)
            return ActionResult(True)
        if t == "click_mouse":
            x = int(params.get("x", 0))
            y = int(params.get("y", 0))
            btn = str(params.get("button", "left")).lower()
            if btn == "right":
                pyautogui.click(x, y, button="right")
            else:
                pyautogui.click(x, y, button="left")
            return ActionResult(True)
        if t == "paste_clipboard":
            text = pyperclip.paste()
            if not text:
                return ActionResult(False, "剪贴板为空")
            return _hotkey("ctrl+v")
        if t == "note":
            return ActionResult(True)
    except Exception as exc:
        _logger.exception("Automation step failed")
        return ActionResult(False, str(exc))
    return ActionResult(False, f"未知步骤类型: {t}")


def _hotkey(keys: str) -> ActionResult:
    parts = [p.strip().lower() for p in re.split(r"[+，,]", keys) if p.strip()]
    alias = {
        "control": "ctrl",
        "win": "win",
        "windows": "win",
        "cmd": "command",
        "esc": "escape",
    }
    norm: list[str] = []
    for p in parts:
        norm.append(alias.get(p, p))
    if sys.platform == "darwin":
        for i, p in enumerate(norm):
            if p == "ctrl":
                norm[i] = "command"
    pyautogui.hotkey(*norm)
    return ActionResult(True)


def _activate_window(title_contains: str) -> ActionResult:
    if sys.platform != "win32":
        _logger.warning("activate_window 仅在 Windows 上可用；当前平台已跳过。")
        return ActionResult(True, "(非 Windows，已跳过激活窗口)")
    try:
        import pygetwindow as gw
    except ImportError:
        return ActionResult(False, "未安装 pygetwindow，无法激活窗口")
    matches = []
    for w in gw.getAllWindows():
        title = w.title or ""
        if title_contains in title:
            matches.append(w)
    if not matches:
        return ActionResult(False, f"未找到标题包含「{title_contains}」的窗口")
    try:
        matches[0].activate()
    except Exception as exc:
        return ActionResult(False, f"激活窗口失败：{exc}")
    return ActionResult(True)
