"""Safe boolean conditions for flow ``if`` steps — no eval(), no ast.exec."""

from __future__ import annotations

import re
from typing import Any

_MAX_REGEX_PATTERN_LEN = 400
_MAX_REGEX_TEXT_LEN = 200_000


def _s(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def evaluate_condition(cond: dict[str, Any]) -> bool:
    """
    Evaluate a small JSON-safe condition object.

    Supported ``op`` values (case-insensitive):

    - ``equals`` / ``eq`` / ``==``: ``left`` vs ``right``
    - ``not_equals`` / ``ne`` / ``!=``
    - ``contains``: ``substring`` in ``text`` (aliases: ``needle``/``right`` → substring;
      ``left`` → text)
    - ``not_contains``
    - ``is_empty``: ``value`` strips to empty
    - ``not_empty``
    - ``matches``: regex ``pattern`` against ``text`` (``re.search``, DOTALL)
    """
    if not isinstance(cond, dict):
        raise ValueError("condition 必须是 JSON 对象")
    op_raw = cond.get("op", "")
    op = _s(op_raw).lower().strip()
    if not op:
        raise ValueError("condition 缺少 op")

    if op in ("equals", "eq", "=="):
        return _s(cond.get("left")) == _s(cond.get("right"))
    if op in ("not_equals", "ne", "!="):
        return _s(cond.get("left")) != _s(cond.get("right"))

    if op == "contains":
        text = _s(cond.get("text", cond.get("left")))
        sub = _s(cond.get("substring", cond.get("needle", cond.get("right"))))
        return sub in text
    if op == "not_contains":
        text = _s(cond.get("text", cond.get("left")))
        sub = _s(cond.get("substring", cond.get("needle", cond.get("right"))))
        return sub not in text

    if op == "is_empty":
        return not _s(cond.get("value")).strip()
    if op == "not_empty":
        return bool(_s(cond.get("value")).strip())

    if op == "matches":
        text = _s(cond.get("text", cond.get("left")))
        pattern = _s(cond.get("pattern", cond.get("right")))
        if len(pattern) > _MAX_REGEX_PATTERN_LEN:
            raise ValueError("正则 pattern 过长")
        if len(text) > _MAX_REGEX_TEXT_LEN:
            raise ValueError("匹配文本过长")
        if not pattern:
            raise ValueError("matches 需要非空 pattern")
        return re.search(pattern, text, flags=re.DOTALL) is not None

    raise ValueError(f"不支持的 condition.op: {op_raw!r}")
