from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from pathlib import Path

_logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 2


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY,
            version INTEGER NOT NULL UNIQUE,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def _max_schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    return int(row[0] or 0)


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    # Table name must be a migration-time literal only (never user-supplied).
    allowed = frozenset({"executions"})
    if table not in allowed:
        raise ValueError(f"Unsupported table for schema check: {table!r}")
    # PRAGMA does not support bound identifiers; `table` is allow-listed above.
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def _migrate_to_v1(conn: sqlite3.Connection) -> None:
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
        """
    )


def _migrate_to_v2(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS step_runs (
            id TEXT PRIMARY KEY,
            execution_id TEXT NOT NULL,
            step_id TEXT,
            order_index INTEGER,
            step_type TEXT,
            status TEXT NOT NULL,
            strategy_used TEXT,
            input_json TEXT,
            output_json TEXT,
            error_message TEXT,
            screenshot_path TEXT,
            started_at TEXT,
            ended_at TEXT,
            FOREIGN KEY (execution_id) REFERENCES executions (id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_step_runs_execution "
        "ON step_runs (execution_id)"
    )

    for col, ddl in (
        ("current_step_id", "TEXT"),
        ("source_file", "TEXT"),
        ("source_sheet", "TEXT"),
        ("source_row_index", "INTEGER"),
    ):
        if not _column_exists(conn, "executions", col):
            conn.execute(f"ALTER TABLE executions ADD COLUMN {col} {ddl}")


_MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {
    1: _migrate_to_v1,
    2: _migrate_to_v2,
}


def init_database(db_path: Path) -> None:
    """Open SQLite, enable WAL, apply embedded migrations sequentially."""
    with connect(db_path) as conn:
        _ensure_migrations_table(conn)
        current = _max_schema_version(conn)
        target = CURRENT_SCHEMA_VERSION
        while current < target:
            next_ver = current + 1
            migrate = _MIGRATIONS.get(next_ver)
            if migrate is None:
                raise RuntimeError(f"No migration defined for version {next_ver}")
            migrate(conn)
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                (next_ver,),
            )
            conn.commit()
            _logger.info("Applied database migration version %s", next_ver)
            current = next_ver
    _logger.info("Database ready at %s (schema %s)", db_path, CURRENT_SCHEMA_VERSION)
