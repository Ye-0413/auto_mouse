from __future__ import annotations

from rpa_assistant.app.ui.flow.canvas.layout_state import (
    ensure_step_ids,
    normalize_canvas_layout,
    reorder_steps_from_layout,
)


def test_ensure_step_ids_fills_missing() -> None:
    steps: list[dict] = [{"type": "wait", "params": {"ms": 1}}]
    ensure_step_ids(steps)
    assert "id" in steps[0] and len(str(steps[0]["id"])) > 8


def test_reorder_steps_from_layout_by_x() -> None:
    a = {"id": "a", "type": "wait", "params": {"ms": 1}}
    b = {"id": "b", "type": "wait", "params": {"ms": 2}}
    c = {"id": "c", "type": "wait", "params": {"ms": 3}}
    steps = [a, b, c]
    layout = {
        "version": 1,
        "positions": {
            "a": [400.0, 0.0],
            "b": [0.0, 0.0],
            "c": [200.0, 0.0],
        },
        "recorded_clusters": [],
    }
    assert reorder_steps_from_layout(steps, canvas_layout=layout) is True
    assert [s["id"] for s in steps] == ["b", "c", "a"]


def test_normalize_canvas_layout_drops_orphan_positions() -> None:
    steps = [{"id": "x", "type": "note", "params": {}}]
    raw = {
        "version": 1,
        "positions": {"x": [1, 2], "ghost": [9, 9]},
        "recorded_clusters": [],
    }
    out = normalize_canvas_layout(raw, steps)
    assert "ghost" not in out["positions"]
    assert out["positions"]["x"] == [1.0, 2.0]
