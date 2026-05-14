"""Human-readable labels and summaries for flow steps (friendly UI)."""

from __future__ import annotations

from typing import Any

STEP_TYPE_LABELS: dict[str, str] = {
    "wait": "等待",
    "input_text": "输入文字",
    "hotkey": "快捷键",
    "activate_window": "激活窗口",
    "open_url": "打开网址",
    "open_file": "打开文件/文件夹",
    "pw_goto": "浏览器：打开网址(CDP)",
    "pw_click_text": "浏览器：点文本(CDP)",
    "pw_inner_text": "浏览器：读文本→变量(CDP)",
    "set_variable": "设置流程变量",
    "click_mouse": "鼠标点击",
    "paste_clipboard": "粘贴剪贴板",
    "if": "条件分支",
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
    if t == "open_file":
        return str(p.get("path", p.get("file", "")))
    if t == "pw_goto":
        u = str(p.get("url", ""))
        return u if len(u) <= 40 else u[:37] + "…"
    if t == "pw_click_text":
        return f"点「{p.get('text', '')}」"
    if t == "pw_inner_text":
        into = str(p.get("into", ""))
        needle = str(p.get("text", ""))
        css = str(p.get("css", p.get("selector", "")))
        if needle:
            src = needle if len(needle) <= 32 else needle[:29] + "…"
            return f"读文本→{into!r}（{src}）"
        cr = css if len(css) <= 32 else css[:29] + "…"
        return f"读文本→{into!r}（CSS:{cr}）"
    if t == "set_variable":
        return f"{p.get('name', p.get('into', ''))} ← {str(p.get('value', ''))[:30]}"
    if t == "click_mouse":
        return f"屏幕坐标 ({p.get('x')}, {p.get('y')}) {p.get('button', 'left')}"
    if t == "paste_clipboard":
        return "向当前焦点粘贴剪贴板内容"
    if t == "if":
        c = p.get("condition")
        if isinstance(c, dict):
            op = str(c.get("op", ""))
            return f"if {op} → then {len(p.get('then') or [])} 步 / else {len(p.get('else') or [])} 步"
        return "条件分支"
    if t == "note":
        return str(p.get("text", ""))[:60]
    return str(p)[:60] if p else "（无参数）"
