"""Dialog to add or edit a single flow step with type-specific forms."""

from __future__ import annotations

import uuid
from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from rpa_assistant.app.ui.flow.presentation import STEP_TYPE_LABELS

# Order matches stack pages
_STEP_ORDER = [
    "wait",
    "input_text",
    "hotkey",
    "activate_window",
    "open_url",
    "click_mouse",
    "paste_clipboard",
    "note",
]


class StepEditorDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        step: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑步骤" if step else "添加步骤")
        self.setMinimumWidth(500)
        self._original_id: str | None = step.get("id") if step else None

        layout = QVBoxLayout(self)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("可选：给这一步起个简短名字，便于辨认")
        layout.addWidget(QLabel("步骤显示名称"))
        layout.addWidget(self._name_edit)

        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("步骤类型"))
        self._type_combo = QComboBox()
        for key in _STEP_ORDER:
            self._type_combo.addItem(STEP_TYPE_LABELS.get(key, key), key)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_row.addWidget(self._type_combo, stretch=1)
        layout.addLayout(type_row)

        self._stack = QStackedWidget()
        self._wait_ms = QSpinBox()
        self._wait_ms.setRange(0, 3_600_000)
        self._wait_ms.setSingleStep(100)
        self._wait_ms.setToolTip("执行到这一步时暂停的毫秒数")

        self._input_text = QLineEdit()
        self._input_text.setPlaceholderText("支持变量，例如：${用户编号}")

        self._hotkey_keys = QLineEdit()
        self._hotkey_keys.setPlaceholderText("例如：ctrl+v 或 alt+tab")

        self._win_title = QLineEdit()
        self._win_title.setPlaceholderText("窗口标题包含这段文字即视为匹配")

        self._url = QLineEdit()
        self._url.setPlaceholderText("https://…")

        click_w = QWidget()
        cform = QFormLayout(click_w)
        self._click_x = QSpinBox()
        self._click_x.setRange(0, 32_000)
        self._click_y = QSpinBox()
        self._click_y.setRange(0, 32_000)
        self._click_btn = QComboBox()
        self._click_btn.addItems(["left", "right"])
        cform.addRow("X（像素）", self._click_x)
        cform.addRow("Y（像素）", self._click_y)
        cform.addRow("鼠标键", self._click_btn)

        paste_w = QWidget()
        pv = QVBoxLayout(paste_w)
        pv.addWidget(
            QLabel(
                "将把当前剪贴板文本粘贴到**已有输入焦点**的控件中。\n"
                "请先激活目标窗口并聚焦输入框。",
            ),
        )

        self._note_text = QLineEdit()
        self._note_text.setPlaceholderText("仅作流程说明，执行时会被跳过")

        self._stack.addWidget(self._wrap_form("等待一段时间，用于页面加载或动画结束。", self._wait_ms))
        self._stack.addWidget(
            self._wrap_form("模拟键盘逐字输入（会发送到当前焦点）。", self._input_text),
        )
        self._stack.addWidget(self._wrap_form("按下组合键。", self._hotkey_keys))
        self._stack.addWidget(self._wrap_form("根据标题找到并激活窗口。", self._win_title))
        self._stack.addWidget(self._wrap_form("在默认浏览器中打开链接（由后续执行器处理）。", self._url))
        self._stack.addWidget(self._wrap_with_hint(click_w, "坐标在分辨率变化时可能失效，优先使用网页/控件定位。"))
        self._stack.addWidget(self._wrap_with_hint(paste_w, ""))
        self._stack.addWidget(self._wrap_form("仅展示在流程列表里，执行引擎可忽略。", self._note_text))

        layout.addWidget(self._stack)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if step:
            self._load_step(step)
        else:
            self._type_combo.setCurrentIndex(0)
            self._on_type_changed()

    def _wrap_form(self, hint: str, field: QWidget) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        if hint:
            lab = QLabel(hint)
            lab.setWordWrap(True)
            lab.setStyleSheet("color: palette(mid);")
            v.addWidget(lab)
        v.addWidget(field)
        return w

    def _wrap_with_hint(self, inner: QWidget, hint: str) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        if hint:
            lab = QLabel(hint)
            lab.setWordWrap(True)
            lab.setStyleSheet("color: palette(mid);")
            v.addWidget(lab)
        v.addWidget(inner)
        return w

    def _on_type_changed(self) -> None:
        idx = self._type_combo.currentIndex()
        if idx >= 0:
            self._stack.setCurrentIndex(idx)

    def _load_step(self, step: dict[str, Any]) -> None:
        self._name_edit.setText(str(step.get("name", "")))
        p: dict[str, Any] = {}
        raw_p = step.get("params")
        if isinstance(raw_p, dict):
            p = raw_p
        elif isinstance(step.get("value"), dict):
            p = step["value"]
        t = step.get("type", "wait")
        idx = self._type_combo.findData(t)
        if idx < 0:
            idx = 0
        self._type_combo.setCurrentIndex(idx)

        self._wait_ms.setValue(int(p.get("ms", 500)))
        self._input_text.setText(str(p.get("text", "")))
        self._hotkey_keys.setText(str(p.get("keys", "")))
        self._win_title.setText(str(p.get("title_contains", "")))
        self._url.setText(str(p.get("url", "")))
        self._click_x.setValue(int(p.get("x", 0)))
        self._click_y.setValue(int(p.get("y", 0)))
        bi = self._click_btn.findText(str(p.get("button", "left")))
        self._click_btn.setCurrentIndex(max(0, bi))
        self._note_text.setText(str(p.get("text", p.get("note", ""))))

        self._stack.setCurrentIndex(idx)

    def get_result(self) -> dict[str, Any]:
        t = self._type_combo.currentData()
        name = self._name_edit.text().strip()
        sid = self._original_id or str(uuid.uuid4())

        params: dict[str, Any] = {}
        if t == "wait":
            params = {"ms": int(self._wait_ms.value())}
        elif t == "input_text":
            params = {"text": self._input_text.text()}
        elif t == "hotkey":
            params = {"keys": self._hotkey_keys.text().strip()}
        elif t == "activate_window":
            params = {"title_contains": self._win_title.text().strip()}
        elif t == "open_url":
            params = {"url": self._url.text().strip()}
        elif t == "click_mouse":
            params = {
                "x": int(self._click_x.value()),
                "y": int(self._click_y.value()),
                "button": self._click_btn.currentText(),
            }
        elif t == "paste_clipboard":
            params = {}
        elif t == "note":
            params = {"text": self._note_text.text().strip()}

        out: dict[str, Any] = {"id": sid, "type": t, "params": params}
        if name:
            out["name"] = name
        return out
