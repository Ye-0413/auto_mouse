from __future__ import annotations

import pytest

from rpa_assistant.app.core.condition_engine import evaluate_condition


def test_equals() -> None:
    assert evaluate_condition({"op": "equals", "left": "a", "right": "a"})
    assert not evaluate_condition({"op": "equals", "left": "a", "right": "b"})


def test_contains() -> None:
    assert evaluate_condition(
        {"op": "contains", "text": "hello world", "substring": "wo"},
    )
    assert not evaluate_condition(
        {"op": "not_contains", "text": "hello world", "substring": "wo"},
    )


def test_empty() -> None:
    assert evaluate_condition({"op": "is_empty", "value": "  "})
    assert evaluate_condition({"op": "not_empty", "value": "x"})


def test_matches() -> None:
    assert evaluate_condition(
        {"op": "matches", "text": "abc123", "pattern": r"\d+"},
    )


def test_unknown_op() -> None:
    with pytest.raises(ValueError, match="不支持"):
        evaluate_condition({"op": "raw_eval", "x": 1})
