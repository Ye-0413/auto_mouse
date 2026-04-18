"""Event capture for mouse and keyboard inputs using pynput."""

import time
import threading
from typing import Callable, Optional, List

import pyautogui
from pynput import mouse, keyboard

from ..data.event import MouseClick, KeyboardInput, Event


class EventCapture:
    """Captures mouse clicks and keyboard inputs."""

    def __init__(
        self,
        on_click: Optional[Callable[[MouseClick], None]] = None,
        on_key: Optional[Callable[[KeyboardInput], None]] = None,
    ):
        self.on_click = on_click
        self.on_key = on_key
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._running: bool = False

    def start(self) -> None:
        """Start capturing mouse and keyboard events."""
        if self._running:
            return

        self._running = True

        # Mouse listener
        self._mouse_listener = mouse.Listener(
            on_click=self._handle_click,
        )
        self._mouse_listener.start()

        # Keyboard listener
        self._keyboard_listener = keyboard.Listener(
            on_press=self._handle_key_press,
            on_release=self._handle_key_release,
        )
        self._keyboard_listener.start()

    def stop(self) -> None:
        """Stop capturing events."""
        self._running = False

        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None

        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None

    def _handle_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        """Handle mouse click events."""
        if not self._running:
            return

        if pressed and self.on_click:
            # Map button to integer
            button_map = {
                mouse.Button.left: 1,
                mouse.Button.right: 2,
                mouse.Button.middle: 3,
            }
            button_num = button_map.get(button, 1)

            click = MouseClick(
                x=int(x),
                y=int(y),
                button=button_num,
                timestamp=time.perf_counter(),
            )
            self.on_click(click)

    def _handle_key_press(self, key) -> None:
        """Handle keyboard press events."""
        if not self._running:
            return

        if self.on_key:
            key_str = self._key_to_string(key)
            event = KeyboardInput(
                key=key_str,
                action="press",
                timestamp=time.perf_counter(),
            )
            self.on_key(event)

    def _handle_key_release(self, key) -> None:
        """Handle keyboard release events."""
        if not self._running:
            return

        if self.on_key:
            key_str = self._key_to_string(key)
            event = KeyboardInput(
                key=key_str,
                action="release",
                timestamp=time.perf_counter(),
            )
            self.on_key(event)

    def _key_to_string(self, key) -> str:
        """Convert a pynput key to a string representation."""
        try:
            if isinstance(key, keyboard.Key):
                return key.name.upper() if hasattr(key, 'name') else str(key).split('.')[-1]
            elif isinstance(key, keyboard.KeyCode):
                if key.char:
                    return key.char
                return str(key.vk)
            return str(key)
        except Exception:
            return str(key)


class EventCaptureWithTrajectory(EventCapture):
    """Event capture that also tracks mouse movement trajectories."""

    def __init__(
        self,
        on_click: Optional[Callable[[MouseClick], None]] = None,
        on_key: Optional[Callable[[KeyboardInput], None]] = None,
        on_trajectory: Optional[Callable[[int, int, float], None]] = None,
        sample_rate: int = 30,
    ):
        super().__init__(on_click=on_click, on_key=on_key)
        self.on_trajectory = on_trajectory
        self.sample_rate = sample_rate
        self._trajectory_thread: Optional[threading.Thread] = None
        self._last_x: int = 0
        self._last_y: int = 0

    def start(self) -> None:
        """Start capturing with trajectory tracking."""
        super().start()
        if self.on_trajectory:
            self._trajectory_thread = threading.Thread(target=self._track_trajectory, daemon=True)
            self._trajectory_thread.start()

    def stop(self) -> None:
        """Stop capturing and trajectory tracking."""
        super().stop()
        if self._trajectory_thread:
            self._trajectory_thread.join(timeout=1)
            self._trajectory_thread = None

    def _track_trajectory(self) -> None:
        """Track mouse trajectory at the specified sample rate."""
        interval = 1.0 / self.sample_rate

        try:
            self._last_x, self._last_y = pyautogui.position()
        except Exception:
            self._last_x, self._last_y = 0, 0

        while self._running:
            try:
                x, y = pyautogui.position()
                if x != self._last_x or y != self._last_y:
                    if self.on_trajectory:
                        self.on_trajectory(x, y, time.perf_counter())
                    self._last_x, self._last_y = x, y
            except Exception:
                pass
            time.sleep(interval)
