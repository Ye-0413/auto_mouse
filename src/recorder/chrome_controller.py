"""Chrome controller for browser automation using Selenium."""

import time
import threading
from typing import Optional, Callable

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from ..config.platform import get_chrome_path, get_chrome_options, IS_WINDOWS
from ..config.settings import CHROME_DEBUG_PORT


class ChromeController:
    """Manages Chrome browser automation with Selenium."""

    def __init__(self, port: int = CHROME_DEBUG_PORT, on_url_change: Optional[Callable[[str], None]] = None):
        self.port = port
        self.on_url_change = on_url_change
        self._driver: Optional[webdriver.Chrome] = None
        self._url_poller: Optional[threading.Thread] = None
        self._last_url: str = ""
        self._running: bool = False

    def launch(self) -> None:
        """Launch a new Chrome browser with debugging enabled."""
        options = Options()
        for opt in get_chrome_options():
            options.add_argument(opt)

        # Set debugging URL
        options.debugger_address = f"127.0.0.1:{self.port}"

        try:
            chrome_path = get_chrome_path()
            if chrome_path and IS_WINDOWS:
                options.binary_location = chrome_path

            service = Service(ChromeDriverManager().install())
            self._driver = webdriver.Chrome(service=service, options=options)
            self._driver.implicitly_wait(5)

        except Exception as e:
            raise RuntimeError(f"Failed to launch Chrome: {e}")

    def attach_to_existing(self) -> bool:
        """Try to attach to an existing Chrome session.

        Returns:
            True if attached successfully, False otherwise.
        """
        options = Options()
        options.debugger_address = f"127.0.0.1:{self.port}"

        try:
            service = Service(ChromeDriverManager().install())
            self._driver = webdriver.Chrome(service=service, options=options)
            self._driver.implicitly_wait(5)
            return True
        except Exception:
            return False

    def get_current_url(self) -> str:
        """Get the current browser URL."""
        if self._driver is None:
            return ""
        try:
            return self._driver.current_url
        except Exception:
            return ""

    def navigate(self, url: str) -> None:
        """Navigate to a specific URL."""
        if self._driver is None:
            raise RuntimeError("Chrome not initialized")
        self._driver.get(url)

    def start_url_polling(self, interval: float = 0.5) -> None:
        """Start polling for URL changes.

        Args:
            interval: Polling interval in seconds.
        """
        self._running = True
        self._last_url = self.get_current_url()

        def poll():
            while self._running:
                try:
                    current_url = self.get_current_url()
                    if current_url != self._last_url and current_url:
                        self._last_url = current_url
                        if self.on_url_change:
                            self.on_url_change(current_url)
                except Exception:
                    pass
                time.sleep(interval)

        self._url_poller = threading.Thread(target=poll, daemon=True)
        self._url_poller.start()

    def stop_url_polling(self) -> None:
        """Stop URL polling."""
        self._running = False
        if self._url_poller:
            self._url_poller.join(timeout=2)
            self._url_poller = None

    def close(self) -> None:
        """Close the Chrome browser."""
        self.stop_url_polling()
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None

    @property
    def is_connected(self) -> bool:
        """Check if Chrome is connected."""
        return self._driver is not None
