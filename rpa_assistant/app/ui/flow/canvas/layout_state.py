"""Persistent layout beside ``definition["steps"]`` — positions + lightweight groups."""

from __future__ import annotations

import uuid
from typing import Any

CANVAS_LAYOUT_KEY = "canvas_layout"


def ensure_step_ids(steps: list[dict[str, Any]]) -> None:
    """Ensure every step has a stable ``id`` (required for画布节点关联)."""
    for s in steps:
        sid = str(s.get("id") or "").strip()
        if sid:
            s["id"] = sid
            continue
        s["id"] = str(uuid.uuid4())


def _pos_x(pos: tuple[float, float] | None, fallback_idx: int, gap: float) -> float:
    if pos is None:
        return float(fallback_idx) * gap
    return float(pos[0])


def reorder_steps_from_layout(
    steps: list[dict[str, Any]],
    *,
    canvas_layout: dict[str, Any] | None,
    gap: float = 224.0,
) -> bool:
    """Sort ``steps`` by saved X (left→右 = 执行顺序). Returns True if order changed."""
    if len(steps) <= 1:
        return False
    layout = canvas_layout if isinstance(canvas_layout, dict) else {}
    positions = layout.get("positions")
    pmap: dict[str, tuple[float, float]] = {}
    if isinstance(positions, dict):
        for k, v in positions.items():
            if not isinstance(k, str):
                continue
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                try:
                    pmap[k] = (float(v[0]), float(v[1]))
                except (TypeError, ValueError):
                    continue
    keyed: list[tuple[float, int, dict[str, Any]]] = []
    for idx, step in enumerate(steps):
        sid = str(step.get("id") or "").strip()
        px = pmap.get(sid)
        keyed.append((_pos_x(px, idx, gap), idx, step))
    keyed_sorted = sorted(keyed, key=lambda t: (t[0], t[1]))
    order_ok = all(keyed_sorted[i][1] == i for i in range(len(keyed_sorted)))
    if order_ok:
        return False
    steps[:] = [t[2] for t in keyed_sorted]
    return True


def build_default_positions(
    steps: list[dict[str, Any]],
    *,
    gap: float = 224.0,
    base_y: float = 48.0,
) -> dict[str, list[float]]:
    ensure_step_ids(steps)
    positions: dict[str, list[float]] = {}
    for i, step in enumerate(steps):
        sid = str(step["id"])
        positions[sid] = [float(i) * gap, base_y]
    return positions


def normalize_canvas_layout(
    canvas_layout: dict[str, Any] | None,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge stored layout + default coordinates for新建/缺失节点."""
    ensure_step_ids(steps)
    merged: dict[str, Any] = {
        "version": 1,
        "positions": {},
        "recorded_clusters": [],
    }
    if isinstance(canvas_layout, dict):
        if canvas_layout.get("version"):
            merged["version"] = int(canvas_layout["version"])
        clusters = canvas_layout.get("recorded_clusters")
        if isinstance(clusters, list):
            merged["recorded_clusters"] = clusters
        pos = canvas_layout.get("positions")
        if isinstance(pos, dict):
            for k, v in pos.items():
                if isinstance(k, str) and isinstance(v, (list, tuple)) and len(v) >= 2:
                    try:
                        merged["positions"][k] = [float(v[0]), float(v[1])]
                    except (TypeError, ValueError):
                        continue

    defaults = build_default_positions(steps)
    for sid, xy in defaults.items():
        merged["positions"].setdefault(sid, xy)
    dead = [
        sid
        for sid in merged["positions"]
        if sid not in {str(s["id"]) for s in steps}
    ]
    for sid in dead:
        del merged["positions"][sid]
    return merged


def steps_snapshot_positions(
    canvas_layout: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    """Write current node positions dict into merged layout blob."""
    out = normalize_canvas_layout(canvas_layout, steps)
    pmap = out["positions"]
    if not isinstance(pmap, dict):
        pmap = {}
    for s in steps:
        sid = str(s.get("id", "")).strip()
        if not sid:
            continue
        if sid not in pmap:
            pmap[sid] = [0.0, 48.0]
    out["positions"] = pmap
    return out
