"""Dialog to add or edit a single flow step with type-specific forms."""

from __future__ import annotations

import json
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
    QMessageBox,
    QPlainTextEdit,
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
    "open_file",
    "pw_goto",
    "pw_click_text",
    "click_mouse",
    "paste_clipboard",
    "if",
    "note",
]

_IF_OPS = [
    "equals",
    "not_equals",
    "contains",
    "not_contains",
    "is_empty",
    "not_empty",
    "matches",
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
        self.setMinimumWidth(520)
        self._minimum_height_if = 420
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

        self._open_path = QLineEdit()
        self._open_path.setPlaceholderText("本地路径，支持 ${变量}，如 D:/报表/输出.xlsx")

        pw_goto_box = QWidget()
        pwgf = QFormLayout(pw_goto_box)
        self._pw_goto_url = QLineEdit()
        self._pw_goto_url.setPlaceholderText("https://…")
        self._pw_goto_cdp = QLineEdit()
        self._pw_goto_cdp.setPlaceholderText("可选：http://127.0.0.1:9222")
        pwgf.addRow("网址", self._pw_goto_url)
        pwgf.addRow("CDP 覆盖（可选）", self._pw_goto_cdp)

        pw_click_box = QWidget()
        pwcf = QFormLayout(pw_click_box)
        self._pw_click_text = QLineEdit()
        self._pw_click_text.setPlaceholderText("页面上可见的文案片段")
        self._pw_click_cdp = QLineEdit()
        self._pw_click_cdp.setPlaceholderText("可选：http://127.0.0.1:9222")
        pwcf.addRow("文本", self._pw_click_text)
        pwcf.addRow("CDP 覆盖（可选）", self._pw_click_cdp)

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

        if_w = QWidget()
        if_l = QVBoxLayout(if_w)
        if_l.addWidget(
            QLabel(
                "根据条件选择执行「then」或「else」下方的步骤数组（JSON）。\n"
                "比较符为 contains 时：左=全文，右=子串；matches 时：左=文本，右=正则。"
                "\nis_empty / not_empty 仅使用左栏作为 value。",
            ),
        )
        if_form = QFormLayout()
        self._if_op = QComboBox()
        for op in _IF_OPS:
            self._if_op.addItem(op, op)
        self._if_left = QLineEdit()
        self._if_left.setPlaceholderText("支持 ${变量名}")
        self._if_right = QLineEdit()
        self._if_right.setPlaceholderText("右操作数、子串或 pattern")
        if_form.addRow("比较符", self._if_op)
        if_form.addRow("左 / 文本 / value", self._if_left)
        if_form.addRow("右 / 子串 / 正则", self._if_right)
        if_box = QWidget()
        if_box.setLayout(if_form)
        if_l.addWidget(if_box)
        self._if_then = QPlainTextEdit()
        self._if_then.setPlaceholderText('[{"type":"wait","params":{"ms":300}}]')
        self._if_then.setMinimumHeight(72)
        self._if_else = QPlainTextEdit()
        self._if_else.setPlaceholderText("[]")
        self._if_else.setMinimumHeight(72)
        if_l.addWidget(QLabel("then（JSON 步骤数组）"))
        if_l.addWidget(self._if_then)
        if_l.addWidget(QLabel("else（JSON 步骤数组）"))
        if_l.addWidget(self._if_else)

        self._note_text = QLineEdit()
        self._note_text.setPlaceholderText("仅作流程说明，执行时会被跳过")

        self._stack.addWidget(self._wrap_form("等待一段时间，用于页面加载或动画结束。", self._wait_ms))
        self._stack.addWidget(
            self._wrap_form("模拟键盘逐字输入（会发送到当前焦点）。", self._input_text),
        )
        self._stack.addWidget(self._wrap_form("按下组合键。", self._hotkey_keys))
        self._stack.addWidget(self._wrap_form("根据标题找到并激活窗口。", self._win_title))
        self._stack.addWidget(self._wrap_form("在默认浏览器中打开链接（由后续执行器处理）。", self._url))
        self._stack.addWidget(
            self._wrap_form(
                "使用系统默认程序打开文件，或在资源管理器/Finder 中打开文件夹。",
                self._open_path,
            ),
        )
        self._stack.addWidget(
            self._wrap_form(
                "Playwright：在已通过 CDP 连接的 Chromium/Chrome 标签中打开网址。"
                "请先在「配置」填写 browser_cdp_url 或在此填写覆盖。需 pip install 'anything-auto[browser]'.",
                pw_goto_box,
            ),
        )
        self._stack.addWidget(
            self._wrap_form(
                "Playwright：点击包含指定可见文本的元素（首个匹配）。",
                pw_click_box,
            ),
        )
        self._stack.addWidget(self._wrap_with_hint(click_w, "坐标在分辨率变化时可能失效，优先使用网页/控件定位。"))
        self._stack.addWidget(self._wrap_with_hint(paste_w, ""))
        self._stack.addWidget(if_w)
        self._stack.addWidget(self._wrap_form("仅展示在流程列表里，执行引擎可忽略。", self._note_text))

        layout.addWidget(self._stack)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.accepted.connect(self._try_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if step:
            self._load_step(step)
        else:
            self._type_combo.setCurrentIndex(0)
            self._on_type_changed()

    def _try_accept(self) -> None:
        t = self._type_combo.currentData()
        if t == "if":
            try:
                json.loads(self._if_then.toPlainText().strip() or "[]")
                json.loads(self._if_else.toPlainText().strip() or "[]")
            except json.JSONDecodeError as exc:
                QMessageBox.warning(
                    self,
                    "条件分支",
                    f"then / else 必须是合法 JSON 数组：\n{exc}",
                )
                return
        self.accept()

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
        if self._type_combo.currentData() == "if":
            self.setMinimumHeight(self._minimum_height_if)
        else:
            self.setMinimumHeight(0)

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
        self._open_path.setText(str(p.get("path", p.get("file", ""))))
        if t == "pw_goto":
            self._pw_goto_url.setText(str(p.get("url", "")))
            self._pw_goto_cdp.setText(str(p.get("cdp_url", "")))
        if t == "pw_click_text":
            self._pw_click_text.setText(str(p.get("text", "")))
            self._pw_click_cdp.setText(str(p.get("cdp_url", "")))
        self._click_x.setValue(int(p.get("x", 0)))
        self._click_y.setValue(int(p.get("y", 0)))
        bi = self._click_btn.findText(str(p.get("button", "left")))
        self._click_btn.setCurrentIndex(max(0, bi))
        self._note_text.setText(str(p.get("text", p.get("note", ""))))

        if t == "if":
            self._load_if_params(p)

        self._stack.setCurrentIndex(idx)

    def _load_if_params(self, p: dict[str, Any]) -> None:
        cond = p.get("condition")
        if not isinstance(cond, dict):
            cond = {}
        op = str(cond.get("op", "equals")).lower()
        if op in ("eq",):
            op = "equals"
        if op in ("ne",):
            op = "not_equals"
        oi = self._if_op.findData(op)
        self._if_op.setCurrentIndex(max(0, oi))
        self._if_left.clear()
        self._if_right.clear()
        if op in ("equals", "not_equals", "==", "!="):
            self._if_left.setText(str(cond.get("left", "")))
            self._if_right.setText(str(cond.get("right", "")))
        elif op in ("contains", "not_contains"):
            self._if_left.setText(str(cond.get("text", cond.get("left", ""))))
            self._if_right.setText(
                str(cond.get("substring", cond.get("needle", cond.get("right", "")))),
            )
        elif op == "matches":
            self._if_left.setText(str(cond.get("text", cond.get("left", ""))))
            self._if_right.setText(str(cond.get("pattern", cond.get("right", ""))))
        elif op in ("is_empty", "not_empty"):
            self._if_left.setText(str(cond.get("value", "")))

        then_steps = p.get("then") or []
        else_steps = p.get("else") or []
        try:
            self._if_then.setPlainText(
                json.dumps(then_steps, ensure_ascii=False, indent=2),
            )
            self._if_else.setPlainText(
                json.dumps(else_steps, ensure_ascii=False, indent=2),
            )
        except TypeError:
            self._if_then.setPlainText("[]")
            self._if_else.setPlainText("[]")

    def _build_if_params(self) -> dict[str, Any]:
        op = str(self._if_op.currentData() or "equals")
        left = self._if_left.text()
        right = self._if_right.text()
        cond: dict[str, Any] = {"op": op}
        if op in ("equals", "not_equals"):
            cond["left"] = left
            cond["right"] = right
        elif op in ("contains", "not_contains"):
            cond["text"] = left
            cond["substring"] = right
        elif op == "matches":
            cond["text"] = left
            cond["pattern"] = right
        elif op in ("is_empty", "not_empty"):
            cond["value"] = left
        then_steps = json.loads(self._if_then.toPlainText().strip() or "[]")
        else_steps = json.loads(self._if_else.toPlainText().strip() or "[]")
        if not isinstance(then_steps, list):
            raise ValueError("then 必须是数组")
        if not isinstance(else_steps, list):
            raise ValueError("else 必须是数组")
        return {
            "condition": cond,
            "then": then_steps,
            "else": else_steps,
        }

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
        elif t == "open_file":
            params = {"path": self._open_path.text().strip()}
        elif t == "pw_goto":
            params = {"url": self._pw_goto_url.text().strip()}
            cdp = self._pw_goto_cdp.text().strip()
            if cdp:
                params["cdp_url"] = cdp
        elif t == "pw_click_text":
            params = {"text": self._pw_click_text.text().strip()}
            cdp = self._pw_click_cdp.text().strip()
            if cdp:
                params["cdp_url"] = cdp
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
        elif t == "if":
            params = self._build_if_params()

        out: dict[str, Any] = {"id": sid, "type": t, "params": params}
        if name:
            out["name"] = name
        return out
