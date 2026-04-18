"""Platform detection and configuration."""

import platform
import sys
from typing import Optional

IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform.startswith("darwin")
IS_LINUX = sys.platform.startswith("linux")


def get_platform() -> str:
    """Returns the current platform: 'windows', 'mac', or 'linux'."""
    if IS_WINDOWS:
        return "windows"
    elif IS_MAC:
        return "mac"
    return "linux"


def get_chrome_path() -> Optional[str]:
    """Returns the platform-specific Chrome binary path."""
    system = get_platform()

    if system == "windows":
        import os
        program_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
        chrome_path = os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe")
        if os.path.exists(chrome_path):
            return chrome_path
        # Try alternate path
        program_files_x86 = os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")
        chrome_path_x86 = os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe")
        if os.path.exists(chrome_path_x86):
            return chrome_path_x86
        return None

    elif system == "mac":
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        import os
        if os.path.exists(chrome_path):
            return chrome_path
        return None

    return None


def get_hotkey_modifier() -> str:
    """Returns the primary hotkey modifier for the current platform."""
    return "ctrl" if IS_WINDOWS else "cmd"


def get_chrome_options() -> list:
    """Returns Chrome options for the current platform."""
    options = [
        f"--remote-debugging-port={9222}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-popup-blocking",
        "--disable-translate",
    ]
    if IS_WINDOWS:
        options.append("--start-maximized")
    else:
        options.append("--kiosk")
    return options
