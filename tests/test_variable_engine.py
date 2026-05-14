from __future__ import annotations

import pytest

from rpa_assistant.app.core.variable_engine import (
    find_unresolved,
    substitute_structure,
    substitute_text,
)
from rpa_assistant.app.models.flow_dsl import validate_flow_definition


def test_substitute_text_ok() -> None:
    assert (
        substitute_text("Hi ${name}", {"name": "Ann"})
        == "Hi Ann"
    )


def test_substitute_text_strict_missing() -> None:
    with pytest.raises(KeyError):
        substitute_text("x=${missing}", {}, strict=True)


def test_substitute_text_lenient() -> None:
    assert substitute_text("x=${missing}", {}, strict=False) == "x=${missing}"


def test_substitute_structure_nested() -> None:
    out = substitute_structure(
        {"a": ["${x}", 1], "b": {"c": "${y}"}},
        {"x": "1", "y": "2"},
    )
    assert out == {"a": ["1", 1], "b": {"c": "2"}}


def test_find_unresolved() -> None:
    assert find_unresolved("a${u}b${v}", {"u": "1"}) == ["v"]


def test_validate_flow_definition() -> None:
    assert validate_flow_definition({}) == ["缺少 steps"]
    assert validate_flow_definition({"steps": "bad"}) == ["steps 必须是数组"]
    errs = validate_flow_definition(
        {"steps": [{"type": "wait"}, {"nope": True}]},
    )
    assert any("步骤 1" in e for e in errs)


def test_validate_if_nested() -> None:
    ok_flow = {
        "steps": [
            {
                "type": "if",
                "params": {
                    "condition": {"op": "equals", "left": "a", "right": "b"},
                    "then": [{"type": "wait", "params": {"ms": 0}}],
                    "else": [],
                },
            },
        ],
    }
    assert validate_flow_definition(ok_flow) == []
    bad = {
        "steps": [
            {
                "type": "if",
                "params": {
                    "condition": "not_an_object",
                    "then": [{"type": "wait", "params": {"ms": 0}}],
                    "else": [],
                },
            },
        ],
    }
    err_b = validate_flow_definition(bad)
    assert any("condition" in e for e in err_b)

    bad_child = {
        "steps": [
            {
                "type": "if",
                "params": {
                    "condition": {"op": "equals", "left": "a", "right": "b"},
                    "then": [{"oops": True}],
                    "else": [],
                },
            },
        ],
    }
    err_c = validate_flow_definition(bad_child)
    assert any("then[0]" in e for e in err_c)
