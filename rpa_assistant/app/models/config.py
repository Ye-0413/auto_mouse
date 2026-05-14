from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import Any


@dataclass
class ConfigPayload:
    """Serialized into configs.payload_json — extend fields as UI grows."""

    excel_file_path: str | None = None
    excel_sheet_name: str | None = None
    excel_header_row: int = 1
    excel_mapping_id: str | None = None
    flow_id: str | None = None
    target_window_title: str | None = None
    target_browser_title: str | None = None
    browser_cdp_url: str | None = None
    default_timeout_ms: int = 30_000
    default_retry_count: int = 0
    screenshot_on_error: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        d = asdict(self)
        extra = d.pop("extra", {}) or {}
        d.update(extra)
        return json.dumps(d, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> ConfigPayload:
        d = json.loads(raw)
        names = {f.name for f in fields(cls)}
        kwargs: dict[str, Any] = {}
        extra: dict[str, Any] = {}
        for key, value in d.items():
            if key in names and key != "extra":
                kwargs[key] = value
            elif key not in names:
                extra[key] = value
        kwargs["extra"] = extra
        return cls(**kwargs)


@dataclass(slots=True)
class ConfigRecord:
    id: str
    name: str
    payload: ConfigPayload
    is_default: bool = False
    created_at: str | None = None
    updated_at: str | None = None
