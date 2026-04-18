"""Event data structures for recording and playback."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Union


class EventType(Enum):
    CLICK = "click"
    KEYBOARD = "keyboard"
    TRAJECTORY_SEGMENT = "trajectory"
    URL_CHANGE = "url_change"


@dataclass
class MouseClick:
    event_type: EventType = EventType.CLICK
    x: int = 0
    y: int = 0
    button: int = 1  # 1=left, 2=right, 3=middle
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.event_type.value,
            "x": self.x,
            "y": self.y,
            "button": self.button,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MouseClick":
        for field in ("x", "y", "button", "timestamp"):
            if field not in data:
                raise ValueError(f"Missing required field '{field}' in MouseClick")
        return cls(
            x=int(data["x"]),
            y=int(data["y"]),
            button=int(data["button"]),
            timestamp=float(data["timestamp"]),
        )


@dataclass
class KeyboardInput:
    event_type: EventType = EventType.KEYBOARD
    key: str = ""
    action: str = "press"  # "press" or "release"
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.event_type.value,
            "key": self.key,
            "action": self.action,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeyboardInput":
        for field in ("key", "action", "timestamp"):
            if field not in data:
                raise ValueError(f"Missing required field '{field}' in KeyboardInput")
        return cls(
            key=str(data["key"]),
            action=str(data["action"]),
            timestamp=float(data["timestamp"]),
        )


@dataclass
class TrajectoryPoint:
    x: int
    y: int
    timestamp: float


@dataclass
class TrajectorySegment:
    event_type: EventType = EventType.TRAJECTORY_SEGMENT
    points: List[TrajectoryPoint] = None
    timestamp: float = 0.0

    def __post_init__(self):
        if self.points is None:
            self.points = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.event_type.value,
            "points": [{"x": p.x, "y": p.y, "timestamp": p.timestamp} for p in self.points],
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrajectorySegment":
        if "points" not in data:
            raise ValueError("Missing required field 'points' in TrajectorySegment")
        if "timestamp" not in data:
            raise ValueError("Missing required field 'timestamp' in TrajectorySegment")
        points = []
        for i, p in enumerate(data["points"]):
            for field in ("x", "y", "timestamp"):
                if field not in p:
                    raise ValueError(f"Missing '{field}' in TrajectorySegment point {i}")
            points.append(TrajectoryPoint(int(p["x"]), int(p["y"]), float(p["timestamp"])))
        return cls(points=points, timestamp=float(data["timestamp"]))


@dataclass
class UrlChange:
    event_type: EventType = EventType.URL_CHANGE
    url: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.event_type.value,
            "url": self.url,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UrlChange":
        for field in ("url", "timestamp"):
            if field not in data:
                raise ValueError(f"Missing required field '{field}' in UrlChange")
        return cls(
            url=str(data["url"]),
            timestamp=float(data["timestamp"]),
        )


Event = Union[MouseClick, KeyboardInput, TrajectorySegment, UrlChange]


def event_to_dict(event: Event) -> Dict[str, Any]:
    """Convert an event to a dictionary."""
    if isinstance(event, MouseClick):
        return event.to_dict()
    elif isinstance(event, KeyboardInput):
        return event.to_dict()
    elif isinstance(event, TrajectorySegment):
        return event.to_dict()
    elif isinstance(event, UrlChange):
        return event.to_dict()
    raise ValueError(f"Unknown event type: {type(event)}")


def dict_to_event(data: Dict[str, Any]) -> Event:
    """Convert a dictionary to an event."""
    event_type = data.get("type")
    if event_type == EventType.CLICK.value:
        return MouseClick.from_dict(data)
    elif event_type == EventType.KEYBOARD.value:
        return KeyboardInput.from_dict(data)
    elif event_type == EventType.TRAJECTORY_SEGMENT.value:
        return TrajectorySegment.from_dict(data)
    elif event_type == EventType.URL_CHANGE.value:
        return UrlChange.from_dict(data)
    raise ValueError(f"Unknown event type: {event_type}")
