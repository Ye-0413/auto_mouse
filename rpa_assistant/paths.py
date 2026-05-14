from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_dir

from rpa_assistant.constants import APP_NAME, APP_ORG, APP_SLUG, ENV_DATA_ROOT


def resolve_data_root() -> Path:
    """Return base directory for SQLite, logs, and screenshots."""
    override = os.environ.get(ENV_DATA_ROOT)
    if override:
        return Path(override).expanduser().resolve()
    return Path(user_data_dir(APP_NAME, APP_ORG), APP_SLUG)


def data_paths() -> tuple[Path, Path, Path, Path]:
    """
    Returns:
        root, database_path, logs_dir, screenshots_dir
    """
    root = resolve_data_root()
    db = root / "data" / "app.sqlite3"
    logs = root / "logs"
    shots = root / "screenshots"
    return root, db, logs, shots


def ensure_app_dirs() -> tuple[Path, Path, Path, Path]:
    root, db, logs, shots = data_paths()
    (root / "data").mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    shots.mkdir(parents=True, exist_ok=True)
    return root, db, logs, shots
