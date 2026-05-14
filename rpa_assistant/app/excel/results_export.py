from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook

from rpa_assistant.app.models.execution import ExecutionRecord


def export_executions_to_xlsx(rows: list[ExecutionRecord], dest: Path) -> None:
    """Write one workbook with one sheet for a batch worth of executions."""
    dest = dest.expanduser().resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "runs"
    headers = (
        "source_row_index",
        "status",
        "error_message",
        "screenshot_path",
        "started_at",
        "ended_at",
        "variables_json",
        "batch_id",
    )
    ws.append(list(headers))
    for ex in sorted(
        rows,
        key=lambda e: (
            e.source_row_index if e.source_row_index is not None else 0,
        ),
    ):
        vars_blob = ""
        if ex.variables is not None:
            try:
                vars_blob = json.dumps(ex.variables, ensure_ascii=False)
            except TypeError:
                vars_blob = str(ex.variables)
        ws.append(
            [
                ex.source_row_index,
                str(ex.status.value if hasattr(ex.status, "value") else ex.status),
                ex.error_message or "",
                ex.screenshot_path or "",
                ex.started_at or "",
                ex.ended_at or "",
                vars_blob,
                ex.batch_id or "",
            ],
        )
    wb.save(dest)
