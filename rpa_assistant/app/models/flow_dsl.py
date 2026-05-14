from __future__ import annotations

from typing import Any


def validate_flow_definition(data: dict[str, Any]) -> list[str]:
    """
    Lightweight structural checks for ``flows.definition_json``.

    Returns a list of human-readable errors (empty if OK).
    """
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["流程定义必须是 JSON 对象"]

    steps = data.get("steps")
    if steps is None:
        errors.append("缺少 steps")
        return errors
    if not isinstance(steps, list):
        errors.append("steps 必须是数组")
        return errors

    for i, step in enumerate(steps):
        prefix = f"步骤 {i}"
        if not isinstance(step, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        t = step.get("type")
        if not isinstance(t, str) or not t.strip():
            errors.append(f"{prefix} 缺少有效的 type")
            continue
        par = step.get("params")
        if par is not None and not isinstance(par, dict):
            errors.append(f"{prefix} 的 params 必须是对象")
        legacy = step.get("value")
        if legacy is not None and not isinstance(legacy, dict):
            errors.append(f"{prefix} 的 value（旧字段）必须是对象")

    return errors
