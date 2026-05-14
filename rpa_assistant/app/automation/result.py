from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ActionResult:
    ok: bool
    message: str = ""
    #: Structured output used by callers (e.g. browser inner_text into variables).
    value: Any | None = None
