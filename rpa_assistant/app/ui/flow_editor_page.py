from __future__ import annotations

from rpa_assistant.app.ui.widgets.placeholder import PlaceholderPage


class FlowEditorPage(PlaceholderPage):
    def __init__(self) -> None:
        super().__init__(
            "流程编辑",
            "创建或编辑步骤序列、变量占位符与条件分支（后续迭代实现）。",
        )
