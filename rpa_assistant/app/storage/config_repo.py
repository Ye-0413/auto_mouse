from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from rpa_assistant.app.models.config import ConfigPayload, ConfigRecord
from rpa_assistant.app.storage.database import connect


def _utc_now() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds")


def _row_to_config(row) -> ConfigRecord:
    return ConfigRecord(
        id=row["id"],
        name=row["name"],
        payload=ConfigPayload.from_json(row["payload_json"]),
        is_default=bool(row["is_default"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class ConfigRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def create(
        self,
        name: str,
        payload: ConfigPayload,
        *,
        record_id: str | None = None,
        is_default: bool = False,
    ) -> str:
        cid = record_id or str(uuid.uuid4())
        now = _utc_now()
        with connect(self._db_path) as conn:
            if is_default:
                conn.execute("UPDATE configs SET is_default = 0")
            conn.execute(
                """
                INSERT INTO configs (id, name, payload_json, is_default, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (cid, name, payload.to_json(), int(is_default), now, now),
            )
            conn.commit()
        return cid

    def get(self, config_id: str) -> ConfigRecord | None:
        with connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM configs WHERE id = ?",
                (config_id,),
            ).fetchone()
        return _row_to_config(row) if row else None

    def list_all(self) -> list[ConfigRecord]:
        with connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM configs ORDER BY updated_at DESC",
            ).fetchall()
        return [_row_to_config(r) for r in rows]

    def get_default(self) -> ConfigRecord | None:
        with connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM configs WHERE is_default = 1 LIMIT 1",
            ).fetchone()
        return _row_to_config(row) if row else None

    def set_default(self, config_id: str) -> bool:
        with connect(self._db_path) as conn:
            conn.execute("UPDATE configs SET is_default = 0")
            cur = conn.execute(
                "UPDATE configs SET is_default = 1 WHERE id = ?",
                (config_id,),
            )
            conn.commit()
            return cur.rowcount == 1

    def save(self, record: ConfigRecord) -> None:
        now = _utc_now()
        with connect(self._db_path) as conn:
            if record.is_default:
                conn.execute("UPDATE configs SET is_default = 0")
            conn.execute(
                """
                UPDATE configs SET
                    name = ?, payload_json = ?, is_default = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    record.name,
                    record.payload.to_json(),
                    int(record.is_default),
                    now,
                    record.id,
                ),
            )
            conn.commit()

    def delete(self, config_id: str) -> bool:
        with connect(self._db_path) as conn:
            cur = conn.execute("DELETE FROM configs WHERE id = ?", (config_id,))
            conn.commit()
            return cur.rowcount > 0
