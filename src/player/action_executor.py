"""Action executor for replaying recorded events using pyautogui."""

import time
from typing import List, Optional

import pyautogui

from ..data.event import (
    MouseClick,
    KeyboardInput,
    TrajectoryPoint,
    TrajectorySegment,
    UrlChange,
)


# Configure pyautogui
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.01  # Small pause between actions


class ActionExecutor:
    """Executes mouse and keyboard actions during playback."""

    def __init__(self):
        self._abort = False

    def abort(self) -> None:
        """Signal the executor to abort current playback."""
        self._abort = True

    def reset_abort(self) -> None:
        """Reset the abort flag."""
        self._abort = False

    def execute_click(self, event: MouseClick) -> None:
        """Execute a mouse click at the specified coordinates."""
        if self._abort:
            return

        try:
            # Map button number to pyautogui button
            button_map = {1: 'left', 2: 'right', 3: 'middle'}
            button = button_map.get(event.button, 'left')

            # Clamp coordinates to screen bounds
            screen_width, screen_height = pyautogui.size()
            x = max(0, min(event.x, screen_width - 1))
            y = max(0, min(event.y, screen_height - 1))

            pyautogui.click(x=x, y=y, button=button)
        except Exception as e:
            print(f"Error executing click at ({event.x}, {event.y}): {e}")

    def execute_keyboard(self, event: KeyboardInput) -> None:
        """Execute a keyboard input."""
        if self._abort:
            return

        try:
            key = event.key

            if event.action == "press":
                # Handle special keys
                if len(key) == 1 and key.isalnum():
                    # Regular character
                    pyautogui.typewrite(key)
                else:
                    # Special key
                    self._press_special_key(key)
            # Release events are typically not needed for typewrite

        except Exception as e:
            print(f"Error executing keyboard event '{key}': {e}")

    def _press_special_key(self, key: str) -> None:
        """Press a special key using pyautogui."""
        key_lower = key.lower()

        # Map common special keys
        special_keys = {
            'ctrl': 'ctrl',
            'control': 'ctrl',
            'alt': 'alt',
            'shift': 'shift',
            'cmd': 'command',
            'command': 'command',
            'enter': 'enter',
            'return': 'enter',
            'tab': 'tab',
            'escape': 'esc',
            'esc': 'esc',
            'space': 'space',
            'backspace': 'backspace',
            'delete': 'delete',
            'up': 'up',
            'down': 'down',
            'left': 'left',
            'right': 'right',
            'home': 'home',
            'end': 'end',
            'page_up': 'pageup',
            'page_down': 'pagedown',
            'f1': 'f1',
            'f2': 'f2',
            'f3': 'f3',
            'f4': 'f4',
            'f5': 'f5',
            'f6': 'f6',
            'f7': 'f7',
            'f8': 'f8',
            'f9': 'f9',
            'f10': 'f10',
            'f11': 'f11',
            'f12': 'f12',
        }

        if key_lower in special_keys:
            pyautogui.press(special_keys[key_lower])
        else:
            # Try to press the key directly
            pyautogui.press(key_lower)

    def execute_trajectory(self, points: List[TrajectoryPoint], speed: float = 1.0) -> None:
        """Execute a trajectory segment by moving the mouse through the points.

        Args:
            points: List of trajectory points.
            speed: Speed multiplier (1.0 = normal, 2.0 = 2x speed).
        """
        if self._abort or not points:
            return

        for i, point in enumerate(points):
            if self._abort:
                return

            try:
                # Calculate duration based on time delta to next point
                if i < len(points) - 1:
                    next_point = points[i + 1]
                    time_delta = (next_point.timestamp - point.timestamp) / speed
                    # Ensure minimum duration
                    duration = max(0.001, min(time_delta, 1.0))
                else:
                    duration = 0.05

                # Clamp coordinates to screen bounds
                screen_width, screen_height = pyautogui.size()
                x = max(0, min(point.x, screen_width - 1))
                y = max(0, min(point.y, screen_height - 1))

                pyautogui.moveTo(x, y, duration=duration)

            except Exception as e:
                print(f"Error executing trajectory at ({point.x}, {point.y}): {e}")
