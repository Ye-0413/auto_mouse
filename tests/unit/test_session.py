"""Unit tests for session module."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from src.data.session import RecordingSession, SessionState
from src.data.event import MouseClick, KeyboardInput, UrlChange, TrajectoryPoint, TrajectorySegment


class TestRecordingSession:
    def test_initial_state(self):
        """Test that a new session starts in IDLE state."""
        session = RecordingSession("test")
        assert session.state == SessionState.IDLE
        assert not session.is_recording
        assert session.duration == 0.0

    def test_start_session(self):
        """Test starting a recording session."""
        session = RecordingSession("test")
        session.start()

        assert session.state == SessionState.RECORDING
        assert session.is_recording

    def test_cannot_start_twice(self):
        """Test that starting an already started session raises error."""
        session = RecordingSession("test")
        session.start()

        with pytest.raises(RuntimeError):
            session.start()

    def test_add_event(self):
        """Test adding events to a session."""
        session = RecordingSession("test")
        session.start()

        click = MouseClick(x=100, y=200, button=1, timestamp=0.0)
        session.add_event(click)

        assert session.get_event_count() == 1

    def test_stop_session(self):
        """Test stopping a recording session."""
        session = RecordingSession("test_session")
        session.start()

        click = MouseClick(x=100, y=200, button=1, timestamp=0.0)
        session.add_event(click)

        time.sleep(0.1)  # Small delay
        recording = session.stop()

        assert session.state == SessionState.STOPPED
        assert recording["name"] == "test_session"
        assert len(recording["events"]) == 1
        assert recording["duration_seconds"] > 0

    def test_cannot_stop_idle_session(self):
        """Test that stopping an IDLE session raises error."""
        session = RecordingSession("test")

        with pytest.raises(RuntimeError):
            session.stop()

    def test_pause_resume(self):
        """Test pausing and resuming a session."""
        session = RecordingSession("test")
        session.start()

        session.pause()
        assert session.state == SessionState.PAUSED

        session.resume()
        assert session.state == SessionState.RECORDING

    def test_click_debounce(self):
        """Test click debouncing."""
        session = RecordingSession("test")
        session.start()

        # First click should be recorded
        assert session.should_record_click(0.0, debounce_ms=200)

        # Click within debounce window should not be recorded
        assert not session.should_record_click(0.1, debounce_ms=200)

        # Click after debounce window should be recorded
        assert session.should_record_click(0.3, debounce_ms=200)


class TestSessionStatistics:
    def test_statistics(self):
        """Test that session statistics are calculated correctly."""
        session = RecordingSession("test")
        session.start()

        session.add_event(MouseClick(x=0, y=0, button=1, timestamp=0.0))
        session.add_event(KeyboardInput(key="a", action="press", timestamp=0.1))
        session.add_event(KeyboardInput(key="b", action="press", timestamp=0.2))
        session.add_event(UrlChange(url="https://example.com", timestamp=0.5))

        recording = session.stop()

        stats = recording["statistics"]
        assert stats["click_count"] == 1
        assert stats["keyboard_event_count"] == 2
        assert stats["url_change_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
