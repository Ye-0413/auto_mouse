from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rpa_assistant.app.models.common import ExecutionStatus, StepRunStatus
from rpa_assistant.app.models.execution import ExecutionRecord, StepRunRecord
from rpa_assistant.app.storage.database import connect


def _utc_now() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds")


def _row_to_execution(row) -> ExecutionRecord:
    vars_json = row["variables_json"]
    variables = json.loads(vars_json) if vars_json else None
    return ExecutionRecord(
        id=row["id"],
        status=ExecutionStatus(row["status"]),
        batch_id=row["batch_id"],
        flow_id=row["flow_id"],
        config_id=row["config_id"],
        variables=variables,
        error_message=row["error_message"],
        screenshot_path=row["screenshot_path"],
        current_step_id=row["current_step_id"],
        source_file=row["source_file"],
        source_sheet=row["source_sheet"],
        source_row_index=row["source_row_index"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
    )


def _row_to_step_run(row) -> StepRunRecord:
    inp = row["input_json"]
    out = row["output_json"]
    return StepRunRecord(
        id=row["id"],
        execution_id=row["execution_id"],
        status=StepRunStatus(row["status"]),
        step_id=row["step_id"],
        order_index=row["order_index"],
        step_type=row["step_type"],
        strategy_used=row["strategy_used"],
        input_data=json.loads(inp) if inp else None,
        output_data=json.loads(out) if out else None,
        error_message=row["error_message"],
        screenshot_path=row["screenshot_path"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
    )


class ExecutionRepository:
    """Persist executions and their step_runs."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def create_execution(
        self,
        record: ExecutionRecord,
        *,
        record_id: str | None = None,
    ) -> str:
        eid = record_id or str(uuid.uuid4())
        vars_json = json.dumps(record.variables, ensure_ascii=False) if record.variables else None
        now = _utc_now()
        started = record.started_at or now
        with connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO executions (
                    id, batch_id, flow_id, config_id, status, variables_json,
                    error_message, screenshot_path, current_step_id,
                    source_file, source_sheet, source_row_index,
                    started_at, ended_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eid,
                    record.batch_id,
                    record.flow_id,
                    record.config_id,
                    record.status.value,
                    vars_json,
                    record.error_message,
                    record.screenshot_path,
                    record.current_step_id,
                    record.source_file,
                    record.source_sheet,
                    record.source_row_index,
                    started,
                    record.ended_at,
                ),
            )
            conn.commit()
        return eid

    def get(self, execution_id: str) -> ExecutionRecord | None:
        with connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM executions WHERE id = ?",
                (execution_id,),
            ).fetchone()
        return _row_to_execution(row) if row else None

    def list_by_batch(self, batch_id: str) -> list[ExecutionRecord]:
        with connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM executions WHERE batch_id = ? ORDER BY started_at",
                (batch_id,),
            ).fetchall()
        return [_row_to_execution(r) for r in rows]

    def list_recent(self, limit: int = 200) -> list[ExecutionRecord]:
        with connect(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM executions
                ORDER BY COALESCE(started_at, '') DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_row_to_execution(r) for r in rows]

    def update(self, record: ExecutionRecord) -> None:
        vars_json = (
            json.dumps(record.variables, ensure_ascii=False) if record.variables else None
        )
        with connect(self._db_path) as conn:
            conn.execute(
                """
                UPDATE executions SET
                    batch_id = ?, flow_id = ?, config_id = ?, status = ?,
                    variables_json = ?, error_message = ?, screenshot_path = ?,
                    current_step_id = ?, source_file = ?, source_sheet = ?,
                    source_row_index = ?, started_at = ?, ended_at = ?
                WHERE id = ?
                """,
                (
                    record.batch_id,
                    record.flow_id,
                    record.config_id,
                    record.status.value,
                    vars_json,
                    record.error_message,
                    record.screenshot_path,
                    record.current_step_id,
                    record.source_file,
                    record.source_sheet,
                    record.source_row_index,
                    record.started_at,
                    record.ended_at,
                    record.id,
                ),
            )
            conn.commit()

    def add_step_run(
        self,
        run: StepRunRecord,
        *,
        record_id: str | None = None,
    ) -> str:
        sid = record_id or str(uuid.uuid4())
        in_j = json.dumps(run.input_data, ensure_ascii=False) if run.input_data else None
        out_j = json.dumps(run.output_data, ensure_ascii=False) if run.output_data else None
        with connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO step_runs (
                    id, execution_id, step_id, order_index, step_type, status,
                    strategy_used, input_json, output_json, error_message,
                    screenshot_path, started_at, ended_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    run.execution_id,
                    run.step_id,
                    run.order_index,
                    run.step_type,
                    run.status.value,
                    run.strategy_used,
                    in_j,
                    out_j,
                    run.error_message,
                    run.screenshot_path,
                    run.started_at,
                    run.ended_at,
                ),
            )
            conn.commit()
        return sid

    def list_step_runs(self, execution_id: str) -> list[StepRunRecord]:
        with connect(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM step_runs WHERE execution_id = ?
                ORDER BY COALESCE(order_index, 999999), rowid
                """,
                (execution_id,),
            ).fetchall()
        return [_row_to_step_run(r) for r in rows]
