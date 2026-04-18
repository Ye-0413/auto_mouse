"""Storage module for saving and loading recordings."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config.settings import RECORDINGS_DIR


class RecordingNotFoundError(Exception):
    """Raised when a recording file is not found."""
    pass


class InvalidRecordingError(Exception):
    """Raised when a recording file is invalid or corrupted."""
    pass


class Storage:
    """Handles saving and loading recordings to/from JSON files."""

    CURRENT_VERSION = "1.0.0"

    def __init__(self, recordings_dir: Optional[str] = None):
        self.recordings_dir = Path(recordings_dir) if recordings_dir else Path(RECORDINGS_DIR)
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

    def save(self, recording: Dict[str, Any], name: Optional[str] = None) -> Path:
        """Save a recording to a JSON file.

        Args:
            recording: The recording dictionary to save.
            name: Optional name for the recording. If not provided, uses timestamp.

        Returns:
            Path to the saved file.
        """
        if name is None:
            name = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Ensure .json extension
        if not name.endswith(".json"):
            name += ".json"

        filepath = self.recordings_dir / name

        # Update name if custom name provided (strip .json for the display name)
        display_name = name[:-5] if name.endswith(".json") else name
        recording["name"] = display_name

        # Add metadata
        recording["version"] = self.CURRENT_VERSION
        recording["saved_at"] = datetime.now().isoformat()

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(recording, f, indent=2, ensure_ascii=False)

        return filepath

    def load(self, name: str) -> Dict[str, Any]:
        """Load a recording from a JSON file.

        Args:
            name: The name of the recording file (with or without .json extension).

        Returns:
            The recording dictionary.

        Raises:
            RecordingNotFoundError: If the file doesn't exist.
            InvalidRecordingError: If the file is invalid or corrupted.
        """
        if not name.endswith(".json"):
            name += ".json"

        filepath = self.recordings_dir / name

        if not filepath.exists():
            raise RecordingNotFoundError(f"Recording not found: {name}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                recording = json.load(f)

            # Validate required fields
            required_fields = ["events", "name", "created_at"]
            for field in required_fields:
                if field not in recording:
                    raise InvalidRecordingError(f"Invalid recording: missing field '{field}'")

            return recording

        except json.JSONDecodeError as e:
            raise InvalidRecordingError(f"Invalid JSON in recording file: {e}")

    def list_recordings(self) -> List[Dict[str, Any]]:
        """List all saved recordings with their metadata.

        Returns:
            List of recording info dictionaries.
        """
        recordings = []

        if not self.recordings_dir.exists():
            return recordings

        for filepath in sorted(self.recordings_dir.glob("*.json"), reverse=True):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                recordings.append({
                    "name": data.get("name", filepath.stem),
                    "filename": filepath.name,
                    "created_at": data.get("created_at", ""),
                    "duration": data.get("duration_seconds", 0),
                    "event_count": len(data.get("events", [])),
                })
            except (json.JSONDecodeError, KeyError):
                # Skip invalid files
                continue

        return recordings

    def delete(self, name: str) -> bool:
        """Delete a recording file.

        Args:
            name: The name of the recording file.

        Returns:
            True if deleted, False if not found.
        """
        if not name.endswith(".json"):
            name += ".json"

        filepath = self.recordings_dir / name

        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def exists(self, name: str) -> bool:
        """Check if a recording exists."""
        if not name.endswith(".json"):
            name += ".json"
        return (self.recordings_dir / name).exists()
