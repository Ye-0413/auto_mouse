# Auto Mouse - Chrome Automation Tool

A cross-platform Chrome automation tool that records user interactions (mouse clicks, keyboard inputs, mouse trajectories, and URL changes) and replays them via a GUI.

## Features

- **Chrome Integration**: Opens Chrome with debugging mode for URL tracking
- **Comprehensive Recording**: Captures mouse clicks, keyboard inputs, mouse movement trajectories, and URL changes
- **Global Hotkey**: Use `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac) to start/stop recording from anywhere
- **GUI Playback**: Visual timeline, playback controls, and speed adjustment
- **Session Management**: Save, load, rename, and delete recordings
- **Cross-Platform**: Supports Windows and macOS

## Requirements

- Python 3.8+
- Google Chrome browser
- Required packages (see `requirements.txt`)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd auto_mouse
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Starting the Application

```bash
python src/main.py
```

Or run directly:
```bash
python -m src.main
```

### Recording

1. Click "New Recording" or press `Ctrl+Shift+R` (Windows) / `Cmd+Shift+R` (Mac)
2. The application will launch Chrome (or attach to an existing Chrome session)
3. Perform your actions in Chrome - they will be recorded
4. Press the hotkey again to stop recording
5. Recording will be saved automatically

### Playback

1. Select a recording from the left panel
2. Click "Play" to start playback
3. Use Pause/Stop to control playback
4. Adjust speed with the dropdown (0.5x, 1x, 2x, 5x)

### Keyboard Shortcuts

| Action | Windows | Mac |
|--------|---------|-----|
| Start/Stop Recording | Ctrl+Shift+R | Cmd+Shift+R |

## Project Structure

```
auto_mouse/
├── src/
│   ├── main.py              # Application entry point
│   ├── config/
│   │   ├── settings.py      # Configuration constants
│   │   └── platform.py      # Platform detection
│   ├── data/
│   │   ├── event.py         # Event data structures
│   │   ├── session.py       # Recording session management
│   │   └── storage.py       # Save/load recordings
│   ├── recorder/
│   │   ├── chrome_controller.py   # Chrome browser control
│   │   ├── event_capture.py       # Mouse/keyboard capture
│   │   └── hotkey_manager.py     # Global hotkey handling
│   ├── player/
│   │   ├── playback_engine.py     # Replay logic
│   │   └── action_executor.py    # Action execution
│   ├── gui/
│   │   └── app.py           # GUI application
│   └── utils/
│       ├── logger.py        # Logging setup
│       └── validators.py     # Input validation
├── tests/
│   └── unit/                # Unit tests
├── recordings/              # Saved recordings (JSON)
└── logs/                   # Application logs
```

## Recording Format

Recordings are saved as JSON files with the following structure:

```json
{
  "version": "1.0.0",
  "name": "recording_name",
  "created_at": "2024-01-01T00:00:00",
  "duration_seconds": 45.7,
  "platform": "windows",
  "events": [
    {"type": "click", "x": 450, "y": 320, "button": 1, "timestamp": 0.0},
    {"type": "keyboard", "key": "a", "action": "press", "timestamp": 0.5},
    {"type": "trajectory", "points": [...], "timestamp": 0.0},
    {"type": "url_change", "url": "https://example.com", "timestamp": 12.5}
  ],
  "statistics": {
    "click_count": 15,
    "keyboard_event_count": 87,
    "trajectory_samples": 342,
    "url_change_count": 3
  }
}
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Building Releases

#### macOS

```bash
./build_release.sh
# Or manually:
pip install pyinstaller
pyinstaller auto_mouse.spec --clean
cd dist
zip -r release/macos/AutoMouse-macos.zip AutoMouse
```

#### Windows

On Windows (with Python installed):
```bash
.\build_release.sh
# Or manually:
pip install pyinstaller
pyinstaller auto_mouse.spec --clean --win-private-assemblies
```

#### Via GitHub Actions (Recommended for cross-platform builds)

Simply push a tag to trigger the release build:
```bash
git tag v1.0.0
git push origin v1.0.0
```

This will automatically build for both macOS and Windows and create a GitHub release.

### Code Quality

The project follows these principles:
- Immutability: Always create new objects, never mutate existing ones
- KISS: Keep it simple
- DRY: Don't repeat yourself
- YAGNI: You aren't gonna need it

## Troubleshooting

### Chrome won't launch

1. Make sure Chrome is installed
2. Check if another Chrome instance is already running with debugging mode
3. Try closing all Chrome windows and restarting

### Hotkey not working

1. Make sure the application window is focused when registering the hotkey
2. Check if the hotkey conflicts with another application

### Playback not accurate

- Ensure the target application is in the same position as during recording
- Mouse coordinates are clamped to screen bounds
- Trajectory playback may vary slightly due to system performance

## License

MIT License
