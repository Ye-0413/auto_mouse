from __future__ import annotations

import re
from typing import Any

_VAR = re.compile(r"\$\{([^}]*)\}")


def substitute_text(
    text: str,
    variables: dict[str, Any],
    *,
    strict: bool = True,
) -> str:
    """
    Replace ``${变量名}`` placeholders. Whitespace inside braces is stripped.

    When ``strict`` is True, raises ``KeyError`` for an unknown name.
    When False, leaves the original placeholder segment unchanged.
    """
    def repl(m: re.Match[str]) -> str:
        key = m.group(1).strip()
        if not key:
            return m.group(0)
        if key in variables:
            return str(variables[key])
        if strict:
            raise KeyError(key)
        return m.group(0)

    return _VAR.sub(repl, text)


def substitute_structure(
    obj: Any,
    variables: dict[str, Any],
    *,
    strict: bool = True,
) -> Any:
    """Walk dict / list and substitute every string leaf."""
    if isinstance(obj, str):
        return substitute_text(obj, variables, strict=strict)
    if isinstance(obj, list):
        return [substitute_structure(x, variables, strict=strict) for x in obj]
    if isinstance(obj, dict):
        return {
            k: substitute_structure(v, variables, strict=strict) for k, v in obj.items()
        }
    return obj


def find_unresolved(text: str, variables: dict[str, Any]) -> list[str]:
    """Return placeholder names that are not present in ``variables``."""
    missing: list[str] = []
    for m in _VAR.finditer(text):
        key = m.group(1).strip()
        if key and key not in variables:
            missing.append(key)
    return missing
