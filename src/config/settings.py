"""Configuration constants for the auto_mouse application."""

TRAJECTORY_SAMPLE_RATE = 30  # Hz
CLICK_DEBOUNCE_MS = 200
MAX_RECORDING_DURATION = 3600  # seconds
CHROME_DRIVER_TIMEOUT = 30  # seconds
DEFAULT_BROWSER_WIDTH = 1280
DEFAULT_BROWSER_HEIGHT = 800
CHROME_DEBUG_PORT = 9222
RECORDINGS_DIR = "recordings"
LOGS_DIR = "logs"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
