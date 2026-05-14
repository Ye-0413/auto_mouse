"""Background recording thread using ``pynput`` (optional dependency).

Trade-off vs fine-grained key logging: printable keys are merged into ``input_text``
after a short idle window so typing becomes fewer steps and matches runner behavior.
Modifier shortcuts are emitted as ``hotkey`` steps. This avoids per-keystep spam but
can merge distinct typing bursts if the pause between them is shorter than the flush delay.
"""

from __future__ import annotations

import threading
from typing import Any

from PySide6.QtCore import QThread, Signal

from rpa_assistant.app.recording.key_mapping import (
    build_hotkey_string,
    mod_token,
    special_hotkey_token,
)
from rpa_assistant.app.recording.step_builders import (
    new_click_mouse_step,
    new_hotkey_step,
    new_input_text_step,
)

_TEXT_FLUSH_SEC = 0.42


class RecorderThread(QThread):
    """Runs ``pynput`` listeners until :meth:`request_stop` is called."""

    step_captured = Signal(dict)
    import_failed = Signal(str)

    def __init__(self, parent: Any | None = None) -> None:
        super().__init__(parent)
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._text_buf: list[str] = []
        self._mods: set[str] = set()
        self._flush_timer: threading.Timer | None = None
        self._mouse_listener: Any = None
        self._key_listener: Any = None

    def request_stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        try:
            from pynput import keyboard, mouse
        except ImportError:
            self.import_failed.emit(
                "未安装 pynput，录制不可用。\n\n请执行：pip install pynput\n"
                "或：pip install \"anything-auto[recorder]\"",
            )
            return

        self._stop.clear()

        self._mouse_listener = mouse.Listener(on_click=self._on_click)
        self._key_listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._mouse_listener.start()
        self._key_listener.start()

        self._stop.wait()

        self._cancel_flush_timer()
        self._flush_text_now()
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._key_listener:
            self._key_listener.stop()
        self._mouse_listener.join()
        self._key_listener.join()

    def _cancel_flush_timer(self) -> None:
        with self._lock:
            if self._flush_timer is not None:
                self._flush_timer.cancel()
                self._flush_timer = None

    def _schedule_text_flush(self) -> None:
        with self._lock:
            if self._flush_timer is not None:
                self._flush_timer.cancel()

            def _fire() -> None:
                self._flush_text_now()

            self._flush_timer = threading.Timer(_TEXT_FLUSH_SEC, _fire)
            self._flush_timer.daemon = True
            self._flush_timer.start()

    def _flush_text_now(self) -> None:
        with self._lock:
            if self._flush_timer is not None:
                self._flush_timer.cancel()
                self._flush_timer = None
            if not self._text_buf:
                return
            text = "".join(self._text_buf)
            self._text_buf.clear()
        if text == "":
            return
        self.step_captured.emit(new_input_text_step(text))

    def _on_click(self, x: float, y: float, button: Any, pressed: bool) -> None:
        try:
            from pynput.mouse import Button
        except ImportError:
            return
        if self._stop.is_set():
            return
        if pressed and button == Button.left:
            self._cancel_flush_timer()
            self._flush_text_now()
            self.step_captured.emit(
                new_click_mouse_step(int(x), int(y), button="left"),
            )

    def _on_press(self, key: Any) -> None:
        if self._stop.is_set():
            return

        try:
            from pynput.keyboard import Key
        except ImportError:
            Key = None  # type: ignore[misc,assignment]
        if Key is not None and key == Key.f12:
            # 全局停止录制（不写入为步骤），便于在其他窗口操作时结束
            self._cancel_flush_timer()
            self._flush_text_now()
            self.request_stop()
            return

        mt = mod_token(key)
        if mt:
            self._mods.add(mt)
            return

        if self._mods & {"ctrl", "alt", "cmd"}:
            self._cancel_flush_timer()
            self._flush_text_now()
            hk = build_hotkey_string(self._mods, key)
            if hk:
                self.step_captured.emit(new_hotkey_step(hk))
            return

        if "shift" in self._mods and special_hotkey_token(key):
            self._cancel_flush_timer()
            self._flush_text_now()
            hk = build_hotkey_string(self._mods, key)
            if hk:
                self.step_captured.emit(new_hotkey_step(hk))
            return

        if Key is None:
            return

        solo = special_hotkey_token(key)
        if solo and not self._mods:
            self._cancel_flush_timer()
            self._flush_text_now()
            self.step_captured.emit(new_hotkey_step(solo))
            return

        if key == Key.backspace:
            self._cancel_flush_timer()
            if self._text_buf:
                self._text_buf.pop()
            return

        if key == Key.space:
            self._text_buf.append(" ")
            self._schedule_text_flush()
            return

        if key == Key.enter:
            self._text_buf.append("\n")
            self._schedule_text_flush()
            return

        ch = getattr(key, "char", None)
        if ch:
            self._text_buf.append(ch)
            self._schedule_text_flush()

    def _on_release(self, key: Any) -> None:
        mt = mod_token(key)
        if mt:
            self._mods.discard(mt)
