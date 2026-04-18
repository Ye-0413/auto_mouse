"""Recording session management."""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .event import Event, EventType
from .storage import Storage
from ..config.platform import get_platform


class SessionState:
    """Enum-like class for session states."""
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"


class RecordingSession:
    """Manages a recording session, collecting events and producing a recording."""

    def __init__(self, name: Optional[str] = None):
        self.name = name or datetime.now().strftime("%Y%m%d_%H%M%S")
        self._state = SessionState.IDLE
        self._events: List[Event] = []
        self._start_time: Optional[float] = None
        self._pause_time: Optional[float] = None
        self._total_paused_time: float = 0.0
        self._last_url: str = ""
        self._last_click_time: float = -1.0

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_recording(self) -> bool:
        return self._state == SessionState.RECORDING

    @property
    def start_time(self) -> Optional[float]:
        """Get the session start time (None if not started)."""
        return self._start_time

    @property
    def duration(self) -> float:
        """Get the current duration in seconds."""
        if self._start_time is None:
            return 0.0
        if self._state == SessionState.RECORDING:
            return time.perf_counter() - self._start_time - self._total_paused_time
        elif self._state == SessionState.STOPPED:
            return self._events[-1].timestamp if self._events else 0.0
        return 0.0

    def start(self) -> None:
        """Start a new recording session."""
        if self._state != SessionState.IDLE:
            raise RuntimeError(f"Cannot start session in state: {self._state}")
        self._state = SessionState.RECORDING
        self._start_time = time.perf_counter()
        self._events = []
        self._total_paused_time = 0.0

    def add_event(self, event: Event) -> None:
        """Add an event to the session."""
        if self._state != SessionState.RECORDING:
            return

        # Adjust timestamp relative to session start
        if self._start_time is not None:
            event.timestamp = time.perf_counter() - self._start_time - self._total_paused_time

        self._events.append(event)

    def pause(self) -> None:
        """Pause the recording."""
        if self._state != SessionState.RECORDING:
            return
        self._state = SessionState.PAUSED
        self._pause_time = time.perf_counter()

    def resume(self) -> None:
        """Resume the recording."""
        if self._state != SessionState.PAUSED:
            return
        if self._pause_time is not None:
            self._total_paused_time += time.perf_counter() - self._pause_time
        self._pause_time = None
        self._state = SessionState.RECORDING

    def stop(self) -> Dict[str, Any]:
        """Stop the session and return the recording data."""
        if self._state not in (SessionState.RECORDING, SessionState.PAUSED):
            raise RuntimeError(f"Cannot stop session in state: {self._state}")

        self._state = SessionState.STOPPED

        # Calculate statistics
        click_count = sum(1 for e in self._events if e.event_type == EventType.CLICK)
        keyboard_count = sum(1 for e in self._events if e.event_type == EventType.KEYBOARD)
        trajectory_count = sum(1 for e in self._events if e.event_type == EventType.TRAJECTORY_SEGMENT)
        url_change_count = sum(1 for e in self._events if e.event_type == EventType.URL_CHANGE)

        # Build recording dictionary
        from .event import event_to_dict
        recording = {
            "version": "1.0.0",
            "name": self.name,
            "created_at": datetime.now().isoformat(),
            "duration_seconds": self.duration,
            "platform": get_platform(),
            "events": [event_to_dict(e) for e in self._events],
            "statistics": {
                "click_count": click_count,
                "keyboard_event_count": keyboard_count,
                "trajectory_samples": trajectory_count,
                "url_change_count": url_change_count,
            },
        }

        return recording

    def get_event_count(self) -> int:
        """Get the number of events recorded."""
        return len(self._events)

    def should_record_click(self, timestamp: float, debounce_ms: int = 200) -> bool:
        """Check if a click should be recorded based on debounce."""
        # Use -1 as sentinel for "no previous click"
        if self._last_click_time < 0:
            self._last_click_time = timestamp
            return True
        if timestamp - self._last_click_time < debounce_ms / 1000:
            return False
        self._last_click_time = timestamp
        return True
