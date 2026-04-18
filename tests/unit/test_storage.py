"""Unit tests for storage module."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from src.data.storage import Storage, RecordingNotFoundError, InvalidRecordingError


class TestStorage:
    @pytest.fixture
    def temp_storage(self):
        """Create a temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Storage(recordings_dir=tmpdir)

    @pytest.fixture
    def sample_recording(self):
        """Create a sample recording."""
        return {
            "name": "test_recording",
            "created_at": "2024-01-01T00:00:00",
            "duration_seconds": 10.5,
            "platform": "windows",
            "events": [
                {"type": "click", "x": 100, "y": 200, "button": 1, "timestamp": 0.0},
                {"type": "keyboard", "key": "a", "action": "press", "timestamp": 0.5},
            ],
            "statistics": {
                "click_count": 1,
                "keyboard_event_count": 1,
                "trajectory_samples": 0,
                "url_change_count": 0,
            },
        }

    def test_save_and_load(self, temp_storage, sample_recording):
        """Test saving and loading a recording."""
        filepath = temp_storage.save(sample_recording, "test_save")

        assert filepath.exists()
        assert filepath.name == "test_save.json"

        loaded = temp_storage.load("test_save")
        assert loaded["name"] == "test_save"
        assert len(loaded["events"]) == 2

    def test_save_without_name(self, temp_storage, sample_recording):
        """Test saving with auto-generated name."""
        filepath = temp_storage.save(sample_recording)

        assert filepath.exists()
        assert filepath.suffix == ".json"

    def test_load_nonexistent(self, temp_storage):
        """Test loading a nonexistent recording."""
        with pytest.raises(RecordingNotFoundError):
            temp_storage.load("nonexistent")

    def test_load_invalid_json(self, temp_storage):
        """Test loading an invalid JSON file."""
        # Create invalid JSON file
        filepath = temp_storage.recordings_dir / "invalid.json"
        filepath.write_text("not valid json {{{")

        with pytest.raises(InvalidRecordingError):
            temp_storage.load("invalid")

    def test_load_missing_fields(self, temp_storage):
        """Test loading a recording with missing required fields."""
        filepath = temp_storage.recordings_dir / "incomplete.json"
        json.dump({"name": "test"}, filepath.open("w"))

        with pytest.raises(InvalidRecordingError):
            temp_storage.load("incomplete")

    def test_list_recordings(self, temp_storage, sample_recording):
        """Test listing recordings."""
        temp_storage.save(sample_recording, "rec1")
        temp_storage.save(sample_recording, "rec2")

        recordings = temp_storage.list_recordings()

        assert len(recordings) == 2
        names = [r["filename"] for r in recordings]
        assert "rec1.json" in names
        assert "rec2.json" in names

    def test_delete(self, temp_storage, sample_recording):
        """Test deleting a recording."""
        temp_storage.save(sample_recording, "to_delete")

        assert temp_storage.exists("to_delete")
        result = temp_storage.delete("to_delete")
        assert result is True
        assert not temp_storage.exists("to_delete")

    def test_delete_nonexistent(self, temp_storage):
        """Test deleting a nonexistent recording."""
        result = temp_storage.delete("nonexistent")
        assert result is False

    def test_exists(self, temp_storage, sample_recording):
        """Test checking if recording exists."""
        assert not temp_storage.exists("new_rec")

        temp_storage.save(sample_recording, "new_rec")
        assert temp_storage.exists("new_rec")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
