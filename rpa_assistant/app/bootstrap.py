from __future__ import annotations

import logging
from pathlib import Path

from rpa_assistant.app.logging_setup import setup_logging
from rpa_assistant.paths import ensure_app_dirs
from rpa_assistant.app.storage.database import init_database

_logger = logging.getLogger(__name__)


def bootstrap_application() -> tuple[Path, Path, Path, Path]:
    """
    Create directories, configure logging, initialize SQLite (WAL).
    """
    root, db_path, log_dir, shots_dir = ensure_app_dirs()
    setup_logging(log_dir)
    init_database(db_path)
    _logger.info("Application data root: %s", root)
    _logger.info("Database path: %s", db_path)
    return root, db_path, log_dir, shots_dir
