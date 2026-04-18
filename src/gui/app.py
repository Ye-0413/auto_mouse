"""Main GUI application using tkinter."""

import sys
import threading
import time
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ..data.storage import Storage
from ..data.session import RecordingSession, SessionState
from ..data.event import MouseClick, KeyboardInput, TrajectoryPoint, UrlChange, TrajectorySegment
from ..recorder.chrome_controller import ChromeController
from ..recorder.event_capture import EventCaptureWithTrajectory
from ..recorder.hotkey_manager import HotkeyManager
from ..player.playback_engine import PlaybackEngine, PlaybackState
from ..config.settings import TRAJECTORY_SAMPLE_RATE


class AutoMouseApp:
    """Main application class."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Auto Mouse - Chrome Automation")
        self.root.geometry("1000x700")

        # Storage
        self.storage = Storage()

        # Recording state
        self.session: Optional[RecordingSession] = None
        self.chrome: Optional[ChromeController] = None
        self.event_capture: Optional[EventCaptureWithTrajectory] = None
        self.hotkey_manager: Optional[HotkeyManager] = None
        self.trajectory_buffer: list = []
        self.last_trajectory_time: float = 0

        # Playback state
        self.playback_engine: Optional[PlaybackEngine] = None

        # UI state
        self.selected_recording: Optional[str] = None
        self.recordings_list: list = []

        self._setup_ui()
        self._setup_hotkeys()
        self._refresh_recordings_list()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Paned window for resizable panels
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Left panel - Recording list
        left_frame = ttk.LabelFrame(paned, text="Recordings", padding="10")
        paned.add(left_frame, weight=1)

        # Recording listbox
        list_frame = ttk.Frame(left_frame)
        list_frame.grid(row=0, column=0, sticky="nsew")
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)

        self.recording_listbox = tk.Listbox(list_frame, height=20)
        self.recording_listbox.grid(row=0, column=0, sticky="nsew")
        self.recording_listbox.bind("<<ListboxSelect>>", self._on_recording_select)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.recording_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.recording_listbox.configure(yscrollcommand=scrollbar.set)

        # List buttons
        btn_frame = ttk.Frame(left_frame)
        btn_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        ttk.Button(btn_frame, text="New Recording", command=self._on_new_recording).grid(row=0, column=0, padx=2)
        ttk.Button(btn_frame, text="Delete", command=self._on_delete_recording).grid(row=0, column=1, padx=2)
        ttk.Button(btn_frame, text="Rename", command=self._on_rename_recording).grid(row=0, column=2, padx=2)

        # Right panel - Preview and controls
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=3)

        # Recording info
        info_frame = ttk.LabelFrame(right_frame, text="Recording Info", padding="10")
        info_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        right_frame.columnconfigure(0, weight=1)

        self.info_labels = {}
        info_items = [
            ("Name:", "name"),
            ("Duration:", "duration"),
            ("Events:", "events"),
            ("Created:", "created"),
        ]

        for i, (label, key) in enumerate(info_items):
            ttk.Label(info_frame, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=2)
            self.info_labels[key] = ttk.Label(info_frame, text="-")
            self.info_labels[key].grid(row=i, column=1, sticky="w", padx=5, pady=2)

        # Control buttons
        control_frame = ttk.Frame(right_frame)
        control_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.play_btn = ttk.Button(control_frame, text="Play", command=self._on_play, state="disabled")
        self.play_btn.grid(row=0, column=0, padx=2)

        self.pause_btn = ttk.Button(control_frame, text="Pause", command=self._on_pause, state="disabled")
        self.pause_btn.grid(row=0, column=1, padx=2)

        self.stop_btn = ttk.Button(control_frame, text="Stop", command=self._on_stop, state="disabled")
        self.stop_btn.grid(row=0, column=2, padx=2)

        ttk.Label(control_frame, text="Speed:").grid(row=0, column=3, padx=(15, 5))
        self.speed_var = tk.StringVar(value="1.0")
        speed_combo = ttk.Combobox(control_frame, textvariable=self.speed_var, values=["0.5", "1.0", "2.0", "5.0"], width=5)
        speed_combo.grid(row=0, column=4, padx=2)
        speed_combo.bind("<<ComboboxSelected>>", self._on_speed_change)

        ttk.Label(control_frame, text="Loop:").grid(row=0, column=5, padx=(15, 5))
        self.loop_var = tk.StringVar(value="1")
        loop_spin = ttk.Spinbox(control_frame, from_=1, to=100, textvariable=self.loop_var, width=5)
        loop_spin.grid(row=0, column=6, padx=2)
        ttk.Label(control_frame, text="(1-100, 0=∞)").grid(row=0, column=7, padx=(0, 5))

        # Timeline canvas
        timeline_frame = ttk.LabelFrame(right_frame, text="Timeline", padding="10")
        timeline_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        right_frame.rowconfigure(2, weight=1)

        self.timeline_canvas = tk.Canvas(timeline_frame, height=100, bg="white")
        self.timeline_canvas.grid(row=0, column=0, sticky="nsew")
        timeline_frame.columnconfigure(0, weight=1)
        timeline_frame.rowconfigure(0, weight=1)

        # Bottom status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=1, column=0, sticky="ew")

        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.grid(row=0, column=0, sticky="w")

        self.recording_indicator = tk.Label(status_frame, text="", bg="gray", width=3)
        self.recording_indicator.grid(row=0, column=1, padx=10)

        ttk.Label(status_frame, text="Press Ctrl+Shift+R to toggle recording").grid(row=0, column=2, sticky="e")

    def _setup_hotkeys(self) -> None:
        """Set up global hotkeys."""
        def on_hotkey(action: str):
            if action == "toggle_recording":
                self.root.after(0, self._toggle_recording)

        self.hotkey_manager = HotkeyManager(on_hotkey)
        self.hotkey_manager.register()

    def _toggle_recording(self) -> None:
        """Toggle recording state."""
        if self.session is None or self.session.state == SessionState.IDLE:
            self._start_recording()
        elif self.session.state == SessionState.RECORDING:
            self._stop_recording()
        elif self.session.state == SessionState.PAUSED:
            self._resume_recording()
        elif self.session.state == SessionState.STOPPED:
            self._start_recording()

    def _start_recording(self) -> None:
        """Start a new recording session."""
        try:
            # Initialize Chrome
            self.chrome = ChromeController(on_url_change=self._on_url_change)
            try:
                self.chrome.launch()
            except Exception:
                # Try to attach to existing
                if not self.chrome.attach_to_existing():
                    messagebox.showerror("Chrome Error", "Could not launch or attach to Chrome. Make sure Chrome is installed and not already running in debugging mode.")
                    return

            self.chrome.start_url_polling()

            # Create session
            self.session = RecordingSession()
            self.session.start()

            # Trajectory buffer
            self.trajectory_buffer = []

            # Initialize event capture
            self.event_capture = EventCaptureWithTrajectory(
                on_click=self._on_capture_click,
                on_key=self._on_capture_key,
                on_trajectory=self._on_capture_trajectory,
                sample_rate=TRAJECTORY_SAMPLE_RATE,
            )
            self.event_capture.start()

            # Update UI
            self._set_recording_ui(True)
            self.status_label.config(text="Recording...")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start recording: {e}")

    def _stop_recording(self) -> None:
        """Stop the current recording."""
        if not self.session:
            return

        # Stop capture
        if self.event_capture:
            self.event_capture.stop()
            self.event_capture = None

        # Stop Chrome polling
        if self.chrome:
            self.chrome.stop_url_polling()
            self.chrome.close()
            self.chrome = None

        # Flush remaining trajectory
        if self.trajectory_buffer:
            self._flush_trajectory()

        # Stop session
        recording = self.session.stop()

        # Save
        filepath = self.storage.save(recording)
        self.session = None

        # Update UI
        self._set_recording_ui(False)
        self.status_label.config(text=f"Saved: {filepath.name}")
        self._refresh_recordings_list()

    def _pause_recording(self) -> None:
        """Pause the current recording."""
        if self.session and self.session.is_recording:
            self.session.pause()
            self.status_label.config(text="Recording (Paused)")

    def _resume_recording(self) -> None:
        """Resume the recording."""
        if self.session and self.session.state == SessionState.PAUSED:
            self.session.resume()
            self.status_label.config(text="Recording...")

    def _on_capture_click(self, event: MouseClick) -> None:
        """Handle captured mouse click."""
        if not self.session or not self.session.is_recording:
            return

        # Debounce clicks
        if not self.session.should_record_click(event.timestamp):
            return

        # Flush trajectory first
        self._flush_trajectory()

        # Scale coordinates if needed (for HiDPI displays)
        event.x = int(event.x)
        event.y = int(event.y)

        self.session.add_event(event)

    def _on_capture_key(self, event: KeyboardInput) -> None:
        """Handle captured keyboard input."""
        if not self.session or not self.session.is_recording:
            return

        self._flush_trajectory()
        self.session.add_event(event)

    def _on_capture_trajectory(self, x: int, y: int, timestamp: float) -> None:
        """Handle captured mouse trajectory."""
        if not self.session or not self.session.is_recording:
            return

        # Add to buffer
        self.trajectory_buffer.append(TrajectoryPoint(int(x), int(y), timestamp))

        # Flush if buffer is large enough
        if len(self.trajectory_buffer) >= 10:
            self._flush_trajectory()

    def _flush_trajectory(self) -> None:
        """Flush the trajectory buffer as a segment."""
        if not self.trajectory_buffer or not self.session:
            return

        if self.session.start_time is None:
            return

        # Calculate relative timestamps
        base_time = self.session.start_time
        points = []
        for point in self.trajectory_buffer:
            relative_ts = point.timestamp - base_time - self.session._total_paused_time
            points.append(TrajectoryPoint(point.x, point.y, max(0, relative_ts)))

        if points:
            segment = TrajectorySegment(points=points, timestamp=points[0].timestamp)
            self.session.add_event(segment)

        self.trajectory_buffer = []

    def _on_url_change(self, url: str) -> None:
        """Handle URL change from Chrome."""
        if not self.session or not self.session.is_recording:
            return

        self._flush_trajectory()
        event = UrlChange(url=url, timestamp=time.perf_counter())
        self.session.add_event(event)

    def _set_recording_ui(self, recording: bool) -> None:
        """Update UI for recording state."""
        if recording:
            self.recording_indicator.config(bg="red")
            self.play_btn.config(state="disabled")
            self.pause_btn.config(state="normal")
            self.stop_btn.config(state="normal")
        else:
            self.recording_indicator.config(bg="gray")
            self.pause_btn.config(state="disabled")

    def _refresh_recordings_list(self) -> None:
        """Refresh the recordings listbox."""
        self.recordings_list = self.storage.list_recordings()
        self.recording_listbox.delete(0, tk.END)

        for rec in self.recordings_list:
            display_name = f"{rec['name']} ({rec.get('duration', 0):.1f}s)"
            self.recording_listbox.insert(tk.END, display_name)

    def _on_recording_select(self, event) -> None:
        """Handle recording selection."""
        selection = self.recording_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        if idx < len(self.recordings_list):
            self.selected_recording = self.recordings_list[idx]["filename"]
            self._load_recording_info(self.recordings_list[idx])
            self.play_btn.config(state="normal")

    def _load_recording_info(self, info: dict) -> None:
        """Load and display recording info."""
        self.info_labels["name"].config(text=info.get("name", "-"))
        self.info_labels["duration"].config(text=f"{info.get('duration', 0):.1f}s")
        self.info_labels["events"].config(text=str(info.get('event_count', 0)))
        self.info_labels["created"].config(text=info.get('created_at', "-")[:19] if info.get('created_at') else "-")

        # Draw timeline
        self._draw_timeline()

    def _draw_timeline(self) -> None:
        """Draw the timeline visualization."""
        self.timeline_canvas.delete("all")

        if not self.selected_recording:
            return

        try:
            recording = self.storage.load(self.selected_recording)
            events = recording.get("events", [])
            duration = recording.get("duration_seconds", 1)

            if not events or duration <= 0:
                return

            width = self.timeline_canvas.winfo_width()
            height = self.timeline_canvas.winfo_height()

            # Draw event markers
            for event in events:
                ts = event.get("timestamp", 0)
                x = (ts / duration) * width

                event_type = event.get("type")
                if event_type == "click":
                    color = "blue"
                elif event_type == "keyboard":
                    color = "green"
                elif event_type == "trajectory":
                    color = "gray"
                elif event_type == "url_change":
                    color = "red"
                else:
                    color = "black"

                self.timeline_canvas.create_line(x, 0, x, height, fill=color, width=2)

        except Exception as e:
            print(f"Error drawing timeline: {e}")

    def _on_new_recording(self) -> None:
        """Start a new recording."""
        self._toggle_recording()

    def _on_delete_recording(self) -> None:
        """Delete the selected recording."""
        if not self.selected_recording:
            return

        if messagebox.askyesno("Delete", f"Delete recording '{self.selected_recording}'?"):
            self.storage.delete(self.selected_recording)
            self._refresh_recordings_list()
            self.selected_recording = None
            for label in self.info_labels.values():
                label.config(text="-")
            self.play_btn.config(state="disabled")

    def _on_rename_recording(self) -> None:
        """Rename the selected recording."""
        if not self.selected_recording:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Rename Recording")
        dialog.geometry("300x100")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="New name:").pack(pady=10)
        entry = ttk.Entry(dialog, width=30)
        entry.pack(pady=5)
        entry.insert(0, self.selected_recording.replace(".json", ""))

        def do_rename():
            new_name = entry.get().strip()
            if new_name:
                try:
                    recording = self.storage.load(self.selected_recording)
                    recording["name"] = new_name
                    self.storage.save(recording, self.selected_recording)
                    self._refresh_recordings_list()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to rename: {e}")
            dialog.destroy()

        ttk.Button(dialog, text="Rename", command=do_rename).pack(pady=10)

    def _on_play(self) -> None:
        """Start or resume playback."""
        if not self.selected_recording:
            return

        if self.playback_engine and self.playback_engine.state == PlaybackState.PAUSED:
            self.playback_engine.resume()
            self.pause_btn.config(text="Pause")
            return

        try:
            recording = self.storage.load(self.selected_recording)
            self.playback_engine = PlaybackEngine(recording)
            self.playback_engine.set_speed(float(self.speed_var.get()))

            # Set loop count
            loop_str = self.loop_var.get().strip()
            if loop_str == "0" or loop_str.lower() == "inf":
                self.playback_engine.set_loop_count(0)  # Infinite
            else:
                try:
                    loop_count = int(loop_str)
                    self.playback_engine.set_loop_count(max(1, min(loop_count, 100)))
                except ValueError:
                    self.playback_engine.set_loop_count(1)

            self.playback_engine.set_on_progress(self._on_playback_progress)
            self.playback_engine.set_on_loop_complete(self._on_loop_complete)
            self.playback_engine.play()

            self.pause_btn.config(state="normal", text="Pause")
            self.stop_btn.config(state="normal")
            loop_info = f" (loop {self.playback_engine.get_loop_count()}x)" if self.playback_engine.get_loop_count() > 0 else " (∞)"
            self.status_label.config(text=f"Playing{loop_info}...")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to play: {e}")

    def _on_pause(self) -> None:
        """Pause or resume playback."""
        if not self.playback_engine:
            return

        if self.playback_engine.state == PlaybackState.PLAYING:
            self.playback_engine.pause()
            self.pause_btn.config(text="Resume")
            self.status_label.config(text="Paused")
        elif self.playback_engine.state == PlaybackState.PAUSED:
            self.playback_engine.resume()
            self.pause_btn.config(text="Pause")
            self.status_label.config(text="Playing...")

    def _on_stop(self) -> None:
        """Stop playback."""
        if self.playback_engine:
            self.playback_engine.stop()
            self.playback_engine = None

        self.pause_btn.config(state="disabled", text="Pause")
        self.stop_btn.config(state="disabled")
        self.status_label.config(text="Ready")

    def _on_speed_change(self, event) -> None:
        """Handle speed change."""
        if self.playback_engine:
            self.playback_engine.set_speed(float(self.speed_var.get()))

    def _on_playback_progress(self, current_time: float, current_index: int, total: int, current_loop: int = 1) -> None:
        """Handle playback progress updates."""
        loop_info = f" [{current_loop}/{self.playback_engine.get_loop_count()}]" if self.playback_engine.get_loop_count() > 0 else ""
        self.root.after(0, lambda: self.status_label.config(
            text=f"Playing{loop_info}: {current_time:.1f}s ({current_index}/{total})"
        ))

    def _on_loop_complete(self, completed_loop: int, total_loops: int) -> None:
        """Handle loop completion."""
        loop_info = f"Loop {completed_loop}/{total_loops}" if total_loops > 0 else "Loop complete"
        self.root.after(0, lambda: self.status_label.config(text=loop_info))

    def run(self) -> None:
        """Start the application main loop."""
        self.root.mainloop()

    def cleanup(self) -> None:
        """Clean up resources before exit."""
        if self.event_capture:
            self.event_capture.stop()
        if self.chrome:
            self.chrome.close()
        if self.hotkey_manager:
            self.hotkey_manager.unregister_all()


def main():
    """Application entry point."""
    root = tk.Tk()
    app = AutoMouseApp(root)

    def on_closing():
        app.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    app.run()


if __name__ == "__main__":
    main()
