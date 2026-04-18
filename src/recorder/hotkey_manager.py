"""Global hotkey manager using pynput."""

import threading
from typing import Callable, Set, Optional

from pynput import keyboard

from ..config.platform import get_hotkey_modifier


class HotkeyManager:
    """Manages global hotkey listeners for start/stop recording."""

    def __init__(self, callback: Callable[[str], None]):
        """
        Initialize the hotkey manager.

        Args:
            callback: Function called when hotkey is pressed. Receives "toggle_recording".
        """
        self.callback = callback
        self._listener: Optional[keyboard.Listener] = None
        self._pressed_keys: Set[keyboard.Key] = set()
        self._running = False

    def register(self) -> None:
        """Register the global hotkey listener."""
        if self._running:
            return

        self._running = True
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def unregister_all(self) -> None:
        """Unregister the hotkey listener."""
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._pressed_keys.clear()

    def _on_press(self, key) -> None:
        """Handle key press events."""
        if not self._running:
            return

        self._pressed_keys.add(key)

        # Check for Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
        modifier = get_hotkey_modifier()

        has_ctrl = keyboard.Key.ctrl in self._pressed_keys or any(
            isinstance(k, keyboard.Key) and 'ctrl' in str(k).lower()
            for k in self._pressed_keys
        )
        has_cmd = keyboard.Key.cmd in self._pressed_keys or any(
            isinstance(k, keyboard.Key) and 'cmd' in str(k).lower()
            for k in self._pressed_keys
        )
        has_shift = keyboard.Key.shift in self._pressed_keys

        # Check for 'R' key
        has_r = any(
            (isinstance(k, keyboard.KeyCode) and k.char and k.char.lower() == 'r') or
            (isinstance(k, keyboard.Key) and 'r' in str(k).lower())
            for k in self._pressed_keys
        )

        if has_shift and has_r:
            if (modifier == "ctrl" and has_ctrl) or (modifier == "cmd" and has_cmd):
                self.callback("toggle_recording")

    def _on_release(self, key) -> None:
        """Handle key release events."""
        if key in self._pressed_keys:
            self._pressed_keys.discard(key)


class SimpleHotkeyManager:
    """A simpler hotkey manager that uses keyboard.press and keyboard.release.

    This is an alternative implementation that might be more reliable on some systems.
    """

    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        self._hotkey_thread: Optional[threading.Thread] = None
        self._running = False
        self._last_toggle_time = 0.0
        self._toggle_debounce = 0.5  # seconds

    def register(self) -> None:
        """Start listening for hotkeys in a background thread."""
        if self._running:
            return

        self._running = True
        self._hotkey_thread = threading.Thread(target=self._listen, daemon=True)
        self._hotkey_thread.start()

    def unregister_all(self) -> None:
        """Stop listening for hotkeys."""
        self._running = False
        if self._hotkey_thread:
            self._hotkey_thread.join(timeout=1)
            self._hotkey_thread = None

    def _listen(self) -> None:
        """Listen for hotkey combinations."""
        import time
        from pynput import keyboard

        COMBINATION = {
            frozenset(['ctrl', 'shift', 'r']),
            frozenset(['cmd', 'shift', 'r']),
        }

        current_keys = set()

        def on_press(key):
            nonlocal current_keys
            try:
                key_name = key.name.lower() if hasattr(key, 'name') else str(key).lower()
                if hasattr(key, 'char') and key.char:
                    current_keys.add(key.char.lower())
                else:
                    current_keys.add(key_name)

                # Check if combination matches
                for combo in COMBINATION:
                    if combo.issubset(current_keys):
                        now = time.time()
                        if now - self._last_toggle_time > self._toggle_debounce:
                            self._last_toggle_time = now
                            self.callback("toggle_recording")
            except Exception:
                pass

        def on_release(key):
            nonlocal current_keys
            try:
                key_name = key.name.lower() if hasattr(key, 'name') else str(key).lower()
                if hasattr(key, 'char') and key.char:
                    current_keys.discard(key.char.lower())
                else:
                    current_keys.discard(key_name)
            except Exception:
                pass

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            while self._running:
                listener.wait()
