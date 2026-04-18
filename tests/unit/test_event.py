"""Unit tests for event data structures."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from src.data.event import (
    EventType,
    MouseClick,
    KeyboardInput,
    TrajectoryPoint,
    TrajectorySegment,
    UrlChange,
    event_to_dict,
    dict_to_event,
)


class TestMouseClick:
    def test_to_dict(self):
        click = MouseClick(x=100, y=200, button=1, timestamp=1.5)
        result = click.to_dict()

        assert result["type"] == "click"
        assert result["x"] == 100
        assert result["y"] == 200
        assert result["button"] == 1
        assert result["timestamp"] == 1.5

    def test_from_dict(self):
        data = {"type": "click", "x": 100, "y": 200, "button": 2, "timestamp": 2.0}
        click = MouseClick.from_dict(data)

        assert click.x == 100
        assert click.y == 200
        assert click.button == 2
        assert click.timestamp == 2.0


class TestKeyboardInput:
    def test_to_dict(self):
        key = KeyboardInput(key="a", action="press", timestamp=1.0)
        result = key.to_dict()

        assert result["type"] == "keyboard"
        assert result["key"] == "a"
        assert result["action"] == "press"
        assert result["timestamp"] == 1.0

    def test_from_dict(self):
        data = {"type": "keyboard", "key": "Enter", "action": "press", "timestamp": 0.5}
        key = KeyboardInput.from_dict(data)

        assert key.key == "Enter"
        assert key.action == "press"


class TestTrajectorySegment:
    def test_to_dict(self):
        points = [
            TrajectoryPoint(x=0, y=0, timestamp=0.0),
            TrajectoryPoint(x=10, y=10, timestamp=0.1),
        ]
        segment = TrajectorySegment(points=points, timestamp=0.0)
        result = segment.to_dict()

        assert result["type"] == "trajectory"
        assert len(result["points"]) == 2
        assert result["points"][0]["x"] == 0

    def test_from_dict(self):
        data = {
            "type": "trajectory",
            "points": [
                {"x": 0, "y": 0, "timestamp": 0.0},
                {"x": 50, "y": 50, "timestamp": 0.5},
            ],
            "timestamp": 0.0,
        }
        segment = TrajectorySegment.from_dict(data)

        assert len(segment.points) == 2
        assert segment.points[1].x == 50


class TestUrlChange:
    def test_to_dict(self):
        url_change = UrlChange(url="https://example.com", timestamp=5.0)
        result = url_change.to_dict()

        assert result["type"] == "url_change"
        assert result["url"] == "https://example.com"
        assert result["timestamp"] == 5.0

    def test_from_dict(self):
        data = {"type": "url_change", "url": "https://test.com", "timestamp": 3.0}
        url_change = UrlChange.from_dict(data)

        assert url_change.url == "https://test.com"


class TestEventConversion:
    def test_roundtrip_click(self):
        original = MouseClick(x=100, y=200, button=1, timestamp=1.5)
        as_dict = event_to_dict(original)
        restored = dict_to_event(as_dict)

        assert isinstance(restored, MouseClick)
        assert restored.x == original.x
        assert restored.y == original.y
        assert restored.button == original.button

    def test_roundtrip_keyboard(self):
        original = KeyboardInput(key="ctrl", action="press", timestamp=0.0)
        as_dict = event_to_dict(original)
        restored = dict_to_event(as_dict)

        assert isinstance(restored, KeyboardInput)
        assert restored.key == original.key

    def test_invalid_type_raises(self):
        data = {"type": "invalid_type", "x": 0, "y": 0}
        with pytest.raises(ValueError):
            dict_to_event(data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
