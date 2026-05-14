from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rpa_assistant.app.models.common import FlowStatus


@dataclass(slots=True)
class FlowRecord:
    id: str
    name: str
    definition: dict[str, Any]
    version: int = 1
    status: FlowStatus = FlowStatus.DRAFT
    created_at: str | None = None
    updated_at: str | None = None
