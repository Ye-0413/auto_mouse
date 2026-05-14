"""Human-readable labels and summaries for flow steps (friendly UI)."""

from __future__ import annotations

from typing import Any

STEP_TYPE_LABELS: dict[str, str] = {
    "wait": "等待",
    "input_text": "输入文字",
    "hotkey": "快捷键",
    "activate_window": "激活窗口",
    "open_url": "打开网址",
    "click_mouse": "鼠标点击",
    "paste_clipboard": "粘贴剪贴板",
    "note": "备注（不执行）",
}


def step_type_label(type_id: str) -> str:
    return STEP_TYPE_LABELS.get(type_id, type_id)


def _params(step: dict[str, Any]) -> dict[str, Any]:
    p = step.get("params")
    if isinstance(p, dict):
        return p
    legacy = step.get("value")
    return legacy if isinstance(legacy, dict) else {}


def summarize_step(step: dict[str, Any]) -> str:
    """One-line description for tables and lists."""
    t = step.get("type") or ""
    p = _params(step)
    if t == "wait":
        return f"等待 {int(p.get('ms', 0))} 毫秒"
    if t == "input_text":
        text = str(p.get("text", ""))
        return text if len(text) <= 40 else text[:37] + "…"
    if t == "hotkey":
        return str(p.get("keys", ""))
    if t == "activate_window":
        return f'窗口标题包含「{p.get("title_contains", "")}」'
    if t == "open_url":
        return str(p.get("url", ""))
    if t == "click_mouse":
        return f"屏幕坐标 ({p.get('x')}, {p.get('y')}) {p.get('button', 'left')}"
    if t == "paste_clipboard":
        return "向当前焦点粘贴剪贴板内容"
    if t == "note":
        return str(p.get("text", ""))[:60]
    return str(p)[:60] if p else "（无参数）"
