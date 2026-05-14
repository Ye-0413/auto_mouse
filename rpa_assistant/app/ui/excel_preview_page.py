from __future__ import annotations

from rpa_assistant.app.ui.widgets.placeholder import PlaceholderPage


class ExcelPreviewPage(PlaceholderPage):
    def __init__(self) -> None:
        super().__init__(
            "Excel 数据预览",
            "选择工作簿与工作表，映射列到变量并校验行数据（后续迭代实现）。",
        )
