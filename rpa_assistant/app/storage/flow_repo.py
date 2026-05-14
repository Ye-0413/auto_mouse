from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rpa_assistant.app.models.common import FlowStatus
from rpa_assistant.app.models.flow import FlowRecord
from rpa_assistant.app.storage.database import connect


def _utc_now() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds")


def _row_to_flow(row) -> FlowRecord:
    return FlowRecord(
        id=row["id"],
        name=row["name"],
        definition=json.loads(row["definition_json"]),
        version=int(row["version"]),
        status=FlowStatus(row["status"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class FlowRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def create(
        self,
        name: str,
        definition: dict[str, Any],
        *,
        record_id: str | None = None,
        version: int = 1,
        status: FlowStatus = FlowStatus.DRAFT,
    ) -> str:
        fid = record_id or str(uuid.uuid4())
        now = _utc_now()
        dj = json.dumps(definition, ensure_ascii=False)
        with connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO flows (id, name, definition_json, version, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (fid, name, dj, version, status.value, now, now),
            )
            conn.commit()
        return fid

    def get(self, flow_id: str) -> FlowRecord | None:
        with connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM flows WHERE id = ?",
                (flow_id,),
            ).fetchone()
        return _row_to_flow(row) if row else None

    def list_all(self) -> list[FlowRecord]:
        with connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM flows ORDER BY updated_at DESC",
            ).fetchall()
        return [_row_to_flow(r) for r in rows]

    def save(self, record: FlowRecord) -> None:
        now = _utc_now()
        dj = json.dumps(record.definition, ensure_ascii=False)
        with connect(self._db_path) as conn:
            conn.execute(
                """
                UPDATE flows SET
                    name = ?, definition_json = ?, version = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (record.name, dj, record.version, record.status.value, now, record.id),
            )
            conn.commit()

    def delete(self, flow_id: str) -> bool:
        with connect(self._db_path) as conn:
            cur = conn.execute("DELETE FROM flows WHERE id = ?", (flow_id,))
            conn.commit()
            return cur.rowcount > 0
