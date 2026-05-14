from __future__ import annotations

from rpa_assistant.app.ui.widgets.placeholder import PlaceholderPage


class LogPage(PlaceholderPage):
    def __init__(self) -> None:
        super().__init__(
            "执行日志",
            "批量与逐步执行结果、失败截图与导出（后续迭代实现）。",
        )
