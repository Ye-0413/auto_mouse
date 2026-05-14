from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

_logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def _ensure_schema_version(conn: sqlite3.Connection) -> int:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY,
            version INTEGER NOT NULL UNIQUE,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    row = conn.execute(
        "SELECT MAX(version) FROM schema_migrations"
    ).fetchone()
    return int(row[0] or 0)


def _apply_migrations(conn: sqlite3.Connection, from_version: int) -> None:
    if from_version >= CURRENT_SCHEMA_VERSION:
        return

    # v1: placeholder tables for upcoming repos (minimal columns)
    if from_version < 1:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS configs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS flows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                definition_json TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                batch_id TEXT,
                flow_id TEXT,
                config_id TEXT,
                status TEXT NOT NULL,
                variables_json TEXT,
                error_message TEXT,
                screenshot_path TEXT,
                started_at TEXT,
                ended_at TEXT,
                FOREIGN KEY (flow_id) REFERENCES flows (id),
                FOREIGN KEY (config_id) REFERENCES configs (id)
            );

            INSERT INTO schema_migrations (version) VALUES (1);
            """
        )
        _logger.info("Applied database migration to version 1")

    conn.commit()


def init_database(db_path: Path) -> None:
    """Open SQLite, enable WAL, apply embedded migrations."""
    with connect(db_path) as conn:
        ver = _ensure_schema_version(conn)
        _apply_migrations(conn, ver)
        conn.commit()
    _logger.info("Database ready at %s (schema %s)", db_path, CURRENT_SCHEMA_VERSION)
