from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rpa_assistant.app.models.common import ExecutionStatus, StepRunStatus


@dataclass(slots=True)
class ExecutionRecord:
    id: str
    status: ExecutionStatus
    batch_id: str | None = None
    flow_id: str | None = None
    config_id: str | None = None
    variables: dict[str, Any] | None = None
    error_message: str | None = None
    screenshot_path: str | None = None
    current_step_id: str | None = None
    source_file: str | None = None
    source_sheet: str | None = None
    source_row_index: int | None = None
    started_at: str | None = None
    ended_at: str | None = None


@dataclass(slots=True)
class StepRunRecord:
    id: str
    execution_id: str
    status: StepRunStatus
    step_id: str | None = None
    order_index: int | None = None
    step_type: str | None = None
    strategy_used: str | None = None
    input_data: dict[str, Any] | None = None
    output_data: dict[str, Any] | None = None
    error_message: str | None = None
    screenshot_path: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
