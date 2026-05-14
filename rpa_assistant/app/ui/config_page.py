from __future__ import annotations

from rpa_assistant.app.ui.widgets.placeholder import PlaceholderPage


class ConfigPage(PlaceholderPage):
    def __init__(self) -> None:
        super().__init__(
            "配置与记忆",
            "持久化 Excel 路径、列映射、目标窗口、超时与重试等（后续迭代实现）。",
        )
