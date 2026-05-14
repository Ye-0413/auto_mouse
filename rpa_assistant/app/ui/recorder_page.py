from __future__ import annotations

from rpa_assistant.app.ui.widgets.placeholder import PlaceholderPage


class RecorderPage(PlaceholderPage):
    def __init__(self) -> None:
        super().__init__(
            "录制",
            "录制鼠标、键盘与窗口切换并保存为流程（后续迭代实现）。",
        )
