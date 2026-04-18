"""Playback engine for replaying recorded sessions."""

import time
import threading
from typing import Callable, Dict, List, Optional

from ..data.event import (
    Event,
    EventType,
    MouseClick,
    KeyboardInput,
    TrajectorySegment,
    UrlChange,
    TrajectoryPoint,
    dict_to_event,
)
from .action_executor import ActionExecutor


class PlaybackState:
    """Playback state constants."""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class PlaybackEngine:
    """Engine for playing back recorded sessions."""

    def __init__(self, recording: Dict):
        """
        Initialize the playback engine.

        Args:
            recording: The recording dictionary to play back.
        """
        self.recording = recording
        self.events: List[Event] = []
        self._state = PlaybackState.STOPPED
        self._speed = 1.0
        self._loop_count = 1  # Number of times to replay
        self._current_loop = 1
        self._current_index = 0
        self._executor = ActionExecutor()
        self._play_thread: Optional[threading.Thread] = None
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        self._on_progress: Optional[Callable[[float, int, int, int], None]] = None
        self._on_loop_complete: Optional[Callable[[int, int], None]] = None

        # Parse events
        self._parse_events()

    def _parse_events(self) -> None:
        """Parse the recording events."""
        events_data = self.recording.get("events", [])
        self.events = []

        for event_data in events_data:
            try:
                event = dict_to_event(event_data)
                self.events.append(event)
            except Exception as e:
                print(f"Error parsing event: {e}")
                continue

        # Sort by timestamp
        self.events.sort(key=lambda e: e.timestamp)

    @property
    def state(self) -> str:
        return self._state

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def duration(self) -> float:
        """Get the total duration of the recording."""
        if not self.events:
            return 0.0
        return max(e.timestamp for e in self.events)

    @property
    def current_time(self) -> float:
        """Get the current playback time."""
        if not self.events or self._current_index >= len(self.events):
            return 0.0
        return self.events[self._current_index].timestamp

    def set_speed(self, speed: float) -> None:
        """Set the playback speed multiplier."""
        self._speed = max(0.1, min(speed, 10.0))

    def set_loop_count(self, count: int) -> None:
        """Set the number of times to replay the recording.

        Args:
            count: Number of loops (1-100). Use 0 for infinite loop.
        """
        self._loop_count = max(1, min(count, 100))

    def get_loop_count(self) -> int:
        """Get the current loop count setting."""
        return self._loop_count

    def set_on_progress(self, callback: Callable[[float, int, int, int], None]) -> None:
        """Set a callback for playback progress updates.

        Callback receives: (current_time, current_index, total_events, current_loop)
        """
        self._on_progress = callback

    def set_on_loop_complete(self, callback: Callable[[int, int], None]) -> None:
        """Set a callback for loop completion.

        Callback receives: (completed_loop, total_loops)
        """
        self._on_loop_complete = callback

    def play(self) -> None:
        """Start or resume playback."""
        if self._state == PlaybackState.PLAYING:
            return

        if self._state == PlaybackState.STOPPED:
            self._current_index = 0
            self._executor.reset_abort()

        self._state = PlaybackState.PLAYING
        self._pause_event.set()

        self._play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self._play_thread.start()

    def pause(self) -> None:
        """Pause playback."""
        if self._state != PlaybackState.PLAYING:
            return

        self._state = PlaybackState.PAUSED
        self._pause_event.clear()

    def resume(self) -> None:
        """Resume playback."""
        if self._state != PlaybackState.PAUSED:
            return

        self._state = PlaybackState.PLAYING
        self._pause_event.set()

    def stop(self) -> None:
        """Stop playback and reset to beginning."""
        self._state = PlaybackState.STOPPED
        self._executor.abort()
        self._pause_event.set()
        self._current_index = 0

        if self._play_thread:
            self._play_thread.join(timeout=1)
            self._play_thread = None

    def seek(self, timestamp: float) -> None:
        """Seek to a specific timestamp."""
        if not self.events:
            return

        # Find the event index closest to the timestamp
        for i, event in enumerate(self.events):
            if event.timestamp >= timestamp:
                self._current_index = i
                break
        else:
            self._current_index = len(self.events) - 1

    def _play_loop(self) -> None:
        """Main playback loop running in a background thread."""
        self._current_loop = 1
        loop_infinite = self._loop_count == 0

        while self._state != PlaybackState.STOPPED:
            if not loop_infinite and self._current_loop > self._loop_count:
                break

            start_time = time.perf_counter()
            self._current_index = 0

            # Loop start callback
            if self._current_loop > 1:
                if self._on_loop_complete:
                    self._on_loop_complete(self._current_loop - 1, self._loop_count)

            while self._current_index < len(self.events) and self._state != PlaybackState.STOPPED:
                # Check if paused
                self._pause_event.wait()

                if self._state == PlaybackState.STOPPED:
                    break

                event = self.events[self._current_index]

                # Calculate when this event should fire
                event_time = event.timestamp / self._speed
                elapsed = time.perf_counter() - start_time

                if elapsed < event_time:
                    # Sleep until it's time for this event
                    sleep_time = (event_time - elapsed) / self._speed
                    time.sleep(max(0.001, sleep_time))

                # Execute the event
                self._execute_event(event)

                # Progress callback
                if self._on_progress:
                    self._on_progress(
                        self.current_time,
                        self._current_index,
                        len(self.events),
                        self._current_loop
                    )

                self._current_index += 1

            if loop_infinite:
                self._current_loop += 1
            else:
                self._current_loop += 1

        # Playback complete
        self._state = PlaybackState.STOPPED
        if self._on_loop_complete:
            self._on_loop_complete(self._current_loop - 1, self._loop_count)

    def _execute_event(self, event: Event) -> None:
        """Execute a single event."""
        if isinstance(event, MouseClick):
            self._executor.execute_click(event)
        elif isinstance(event, KeyboardInput):
            self._executor.execute_keyboard(event)
        elif isinstance(event, TrajectorySegment):
            self._executor.execute_trajectory(event.points, self._speed)
        elif isinstance(event, UrlChange):
            # URL changes during playback - could trigger Chrome navigation
            # For now, we just log it
            print(f"[Playback] Would navigate to: {event.url}")
