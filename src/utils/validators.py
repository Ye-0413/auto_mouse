"""Input validation utilities."""

import re
from typing import Any, Optional


def validate_recording_name(name: str) -> tuple[bool, Optional[str]]:
    """Validate a recording name.

    Args:
        name: The recording name to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not name:
        return False, "Name cannot be empty"

    if len(name) > 100:
        return False, "Name cannot exceed 100 characters"

    # Allow alphanumeric, spaces, underscores, hyphens
    if not re.match(r'^[\w\s\-]+$', name):
        return False, "Name can only contain letters, numbers, spaces, underscores, and hyphens"

    return True, None


def validate_url(url: str) -> bool:
    """Validate a URL.

    Args:
        url: The URL to validate.

    Returns:
        True if valid, False otherwise.
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP address
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(url_pattern.match(url))


def validate_coordinates(x: int, y: int, screen_width: int, screen_height: int) -> tuple[bool, int, int]:
    """Validate and clamp screen coordinates.

    Args:
        x: X coordinate.
        y: Y coordinate.
        screen_width: Screen width.
        screen_height: Screen height.

    Returns:
        Tuple of (is_valid, clamped_x, clamped_y).
    """
    clamped_x = max(0, min(x, screen_width - 1))
    clamped_y = max(0, min(y, screen_height - 1))
    return True, clamped_x, clamped_y


def validate_speed(speed: float) -> tuple[bool, float]:
    """Validate playback speed.

    Args:
        speed: Speed multiplier.

    Returns:
        Tuple of (is_valid, clamped_speed).
    """
    clamped_speed = max(0.1, min(speed, 10.0))
    return True, clamped_speed


def validate_recording_data(data: dict) -> tuple[bool, Optional[str]]:
    """Validate recording data structure.

    Args:
        data: Recording dictionary to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    required_fields = ["name", "events", "created_at"]

    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    if not isinstance(data["events"], list):
        return False, "Events must be a list"

    return True, None
