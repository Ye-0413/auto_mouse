"""Dialog to add or edit a single flow step with type-specific forms."""

from __future__ import annotations

import json
import uuid
from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
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

from rpa_assistant.app.models.flow_dsl import validate_flow_definition
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
    "pw_inner_text",
    "set_variable",
    "click_mouse",
    "paste_clipboard",
    "read_clipboard",
    "clear_clipboard",
    "clipboard_switch",
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
    "file_exists",
    "window_exists",
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

        hint = QLabel(
            "请按顺序：先选<b>步骤类型</b>，再填下面出现的参数。"
            "文字里可写 <b>${变量名}</b>，由单次运行时的上下文替换（不再依赖 Excel 列）。"
            "不确定可先随便填，保存后到「运行」页点「运行」验证。"
        )
        hint.setWordWrap(True)
        hint.setOpenExternalLinks(False)
        hint.setStyleSheet(
            "color: palette(mid); padding: 4px 4px 8px 4px; font-size: 12px;",
        )
        layout.addWidget(hint)

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

        pw_inner_w = QWidget()
        pwl = QFormLayout(pw_inner_w)
        self._pw_inner_into = QLineEdit()
        self._pw_inner_into.setPlaceholderText("流程变量名，例如 页面合同类型")
        self._pw_inner_needle = QLineEdit()
        self._pw_inner_needle.setPlaceholderText(
            "按可见文案定位元素（与 CSS 二选一，通常更简单）",
        )
        self._pw_inner_css = QLineEdit()
        self._pw_inner_css.setPlaceholderText("或使用 Playwright CSS locator（与上文二选一）")
        self._pw_inner_nth = QSpinBox()
        self._pw_inner_nth.setRange(0, 9_999)
        self._pw_inner_exact_ck = QCheckBox("文案精确相等（否则子串匹配）")
        self._pw_inner_timeout_ms = QSpinBox()
        self._pw_inner_timeout_ms.setRange(100, 600_000)
        self._pw_inner_timeout_ms.setValue(30_000)
        self._pw_inner_cdp = QLineEdit()
        self._pw_inner_cdp.setPlaceholderText("可选：http://127.0.0.1:9222")
        pwl.addRow("写入变量 into", self._pw_inner_into)
        pwl.addRow("可见文案 text", self._pw_inner_needle)
        pwl.addRow("CSS locator", self._pw_inner_css)
        pwl.addRow("nth（0 起）", self._pw_inner_nth)
        pwl.addRow("", self._pw_inner_exact_ck)
        pwl.addRow("超时毫秒", self._pw_inner_timeout_ms)
        pwl.addRow("CDP 覆盖", self._pw_inner_cdp)

        set_var_w = QWidget()
        svf = QFormLayout(set_var_w)
        self._sv_name = QLineEdit()
        self._sv_name.setPlaceholderText("变量名")
        self._sv_val = QLineEdit()
        self._sv_val.setPlaceholderText("支持 ${映射列变量} ")
        svf.addRow("变量名", self._sv_name)
        svf.addRow("值", self._sv_val)

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

        read_clipboard_w = QWidget()
        rcf = QFormLayout(read_clipboard_w)
        self._clip_into = QLineEdit()
        self._clip_into.setPlaceholderText("默认 _clipboard，可与「剪贴板关键词分支」配合")
        self._clip_strip = QCheckBox("去掉首尾空白（strip）")
        self._clip_strip.setChecked(True)
        rcf.addRow("写入变量 into", self._clip_into)
        rcf.addRow("", self._clip_strip)

        clear_clipboard_w = QWidget()
        ccb = QVBoxLayout(clear_clipboard_w)
        ccb.addWidget(
            QLabel("执行时用 pyperclip 将系统剪贴板置为空字符串。"),
        )

        clip_sw_w = QWidget()
        clip_v = QVBoxLayout(clip_sw_w)
        clip_v.addWidget(
            QLabel(
                "读取已写入流程变量的文本（通常上一步「读取剪贴板→变量」得到），"
                "按规则的 <b>contains_any</b> 子串依次匹配：<b>先命中先执行</b>该规则的 "
                "<b>steps</b>；若<strong>无任何规则命中</strong>，则<strong>立即静默结束整条流程"
                "</strong>（不报错，后面的步骤也不再执行）。\n"
                "关键词与支持 ${变量} 占位（在每条规则的对象里替换）。",
            ),
        )
        clip_form = QFormLayout()
        self._clip_switch_var = QLineEdit("_clipboard")
        self._clip_switch_var.setPlaceholderText("流程变量名，默认 _clipboard")
        self._clip_switch_ci = QCheckBox("子串匹配忽略大小写")
        clip_form.addRow("待匹配变量 variable", self._clip_switch_var)
        clip_form.addRow("", self._clip_switch_ci)
        cfw = QWidget()
        cfw.setLayout(clip_form)
        clip_v.addWidget(cfw)
        self._clip_rules_json = QPlainTextEdit()
        self._clip_rules_json.setPlaceholderText(
            '[\n  {"contains_any": ["高压供电", "工单"], '
            '"steps": [{"type": "wait", "params": {"ms": 300}}]}\n]',
        )
        self._clip_rules_json.setMinimumHeight(120)
        self._clip_rules_json.setAccessibleName("剪贴板关键词分支 rules")
        self._clip_rules_json.setAccessibleDescription("JSON 数组；编辑时会提示语法是否与数组结构粗略匹配。")
        clip_v.addWidget(QLabel('rules（JSON 数组：contains_any / contains + steps）'))
        clip_v.addWidget(self._clip_rules_json)
        self._clip_rules_status = QLabel("")
        self._clip_rules_status.setWordWrap(True)
        self._clip_rules_status.setAccessibleName("rules JSON 校验状态")
        self._clip_rules_status.setStyleSheet("color:#7d8ea1; font-size:12px;")
        clip_v.addWidget(self._clip_rules_status)
        self._clip_rules_json.textChanged.connect(self._refresh_clip_rules_json_status)

        if_w = QWidget()
        if_l = QVBoxLayout(if_w)
        if_l.addWidget(
            QLabel(
                "根据条件选择执行「then」或「else」下方的步骤数组（JSON）。\n"
                "contains：左=全文，右=子串；matches：左=文本，右=正则；"
                "is_empty / not_empty：仅左栏=value。\n"
                "file_exists：左栏=文件路径；window_exists：左栏=窗口标题需包含的子串（Windows）。",
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
        self._if_then.setAccessibleName("条件为真时执行的步骤数组")
        self._if_else.setAccessibleName("条件为假时执行的步骤数组")
        self._if_json_status = QLabel("")
        self._if_json_status.setWordWrap(True)
        self._if_json_status.setAccessibleName("条件分支 JSON 校验状态")
        self._if_json_status.setStyleSheet("color:#7d8ea1; font-size:12px;")
        if_l.addWidget(self._if_json_status)
        self._if_then.textChanged.connect(self._refresh_if_branch_json_status)
        self._if_else.textChanged.connect(self._refresh_if_branch_json_status)

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
        self._stack.addWidget(
            self._wrap_form(
                (
                    "Playwright：读取元素 inner_text 并写入命名变量（CDP）；"
                    "后续步骤可对 ${变量名} 做 if 或使用。"
                ),
                pw_inner_w,
            ),
        )
        self._stack.addWidget(
            self._wrap_form(
                "在运行时设置流程变量（不触发桌面自动化）。",
                set_var_w,
            ),
        )
        self._stack.addWidget(self._wrap_with_hint(click_w, "坐标在分辨率变化时可能失效，优先使用网页/控件定位。"))
        self._stack.addWidget(self._wrap_with_hint(paste_w, ""))
        self._stack.addWidget(
            self._wrap_form(
                "从系统剪贴板读取文本并写入命名变量（不发送按键）。常与「清空剪贴板」"
                "或「粘贴」前后搭配。",
                read_clipboard_w,
            ),
        )
        self._stack.addWidget(self._wrap_with_hint(clear_clipboard_w, ""))
        self._stack.addWidget(clip_sw_w)
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
        elif t == "pw_inner_text":
            if not self._pw_inner_into.text().strip():
                QMessageBox.warning(self, "", "请填写写入变量 into。")
                return
            tn = self._pw_inner_needle.text().strip()
            cs = self._pw_inner_css.text().strip()
            if not tn and not cs:
                QMessageBox.warning(
                    self,
                    "",
                    "请填写「可见文案 text」或「CSS locator」其中之一。",
                )
                return
        elif t == "set_variable":
            if not self._sv_name.text().strip():
                QMessageBox.warning(self, "", "请填写变量名。")
                return
        elif t == "clipboard_switch":
            raw = self._clip_rules_json.toPlainText().strip() or "[]"
            try:
                rules = json.loads(raw)
            except json.JSONDecodeError as exc:
                QMessageBox.warning(
                    self,
                    "剪贴板关键词分支",
                    f"rules 必须是合法 JSON 数组：\n{exc}",
                )
                return
            if not isinstance(rules, list):
                QMessageBox.warning(self, "", "rules 顶层必须是数组。")
                return
            for ri, rule in enumerate(rules):
                if not isinstance(rule, dict):
                    QMessageBox.warning(self, "", f"rules[{ri}] 必须是 JSON 对象。")
                    return
                sub_steps = rule.get("steps")
                if sub_steps is None:
                    sub_steps = []
                errs = validate_flow_definition({"steps": sub_steps})
                if errs:
                    QMessageBox.warning(
                        self,
                        "剪贴板关键词分支",
                        f"rules[{ri}] 子步骤校验：\n" + "\n".join(errs[:12]),
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
        if self._type_combo.currentData() in ("if", "clipboard_switch"):
            self.setMinimumHeight(self._minimum_height_if)
        else:
            self.setMinimumHeight(0)
        self._refresh_clip_rules_json_status()
        self._refresh_if_branch_json_status()

    def _refresh_clip_rules_json_status(self) -> None:
        if self._type_combo.currentData() != "clipboard_switch":
            self._clip_rules_status.clear()
            return
        raw = self._clip_rules_json.toPlainText().strip()
        if not raw:
            self._clip_rules_status.setStyleSheet("color:#7d8ea1; font-size:12px;")
            self._clip_rules_status.setText('留空时将按 "[]" 处理。')
            return
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            self._clip_rules_status.setStyleSheet("color:#e8927a; font-size:12px;")
            self._clip_rules_status.setText(f"JSON 语法有误：第 {exc.lineno} 行附近 — {exc.msg}")
            return
        self._clip_rules_status.setStyleSheet("color:#6abf8e; font-size:12px;")
        if isinstance(parsed, list):
            hint = (
                f"JSON 顶层为数组，长度 {len(parsed)}。"
                "保存时仍会逐项校验每条规则内的 steps。"
            )
        else:
            hint = (
                "JSON 虽已解析成功，但 rules 应为数组。"
                f"当前类型：{type(parsed).__name__}。"
            )
        self._clip_rules_status.setText(hint)

    def _refresh_if_branch_json_status(self) -> None:
        if self._type_combo.currentData() != "if":
            self._if_json_status.clear()
            return
        parts: list[str] = []
        ok = True
        for lab, fld in ("then", self._if_then), ("else", self._if_else):
            raw = fld.toPlainText().strip()
            if not raw and lab == "else":
                raw = "[]"
            try:
                parsed = json.loads(raw or "[]")
            except json.JSONDecodeError as exc:
                ok = False
                parts.append(
                    f"{lab}：语法错误 — 约第 {exc.lineno} 行 {exc.msg}",
                )
                continue
            if not isinstance(parsed, list):
                ok = False
                parts.append(
                    f"{lab}：必须是 JSON 数组，当前为 {type(parsed).__name__}。",
                )
            else:
                parts.append(f"{lab}：{len(parsed)} 个子步骤（数组）")

        self._if_json_status.setStyleSheet(
            "color:#6abf8e; font-size:12px;"
            if ok
            else "color:#e8927a; font-size:12px;",
        )
        self._if_json_status.setText(" · ".join(parts))

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
        if t == "pw_inner_text":
            self._pw_inner_into.setText(str(p.get("into", "")))
            self._pw_inner_needle.setText(str(p.get("text", "")))
            css_v = str(p.get("css", p.get("selector", "")))
            self._pw_inner_css.setText(css_v)
            self._pw_inner_nth.setValue(int(p.get("nth", 0)))
            self._pw_inner_exact_ck.setChecked(bool(p.get("exact", False)))
            self._pw_inner_timeout_ms.setValue(int(p.get("timeout_ms", 30_000)))
            self._pw_inner_cdp.setText(str(p.get("cdp_url", "")))
        if t == "set_variable":
            self._sv_name.setText(str(p.get("name", p.get("into", ""))))
            self._sv_val.setText(str(p.get("value", "")))
        self._click_x.setValue(int(p.get("x", 0)))
        self._click_y.setValue(int(p.get("y", 0)))
        bi = self._click_btn.findText(str(p.get("button", "left")))
        self._click_btn.setCurrentIndex(max(0, bi))
        self._note_text.setText(str(p.get("text", p.get("note", ""))))

        if t == "read_clipboard":
            self._clip_into.setText(str(p.get("into", "")))
            self._clip_strip.setChecked(bool(p.get("strip", True)))
        if t == "clipboard_switch":
            self._clip_switch_var.setText(
                str(p.get("variable", "_clipboard")).strip() or "_clipboard",
            )
            self._clip_switch_ci.setChecked(bool(p.get("case_insensitive", False)))
            rules_arr = p.get("rules") or []
            try:
                self._clip_rules_json.setPlainText(
                    json.dumps(
                        rules_arr,
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
            except TypeError:
                self._clip_rules_json.setPlainText("[]")
        if t == "if":
            self._load_if_params(p)

        self._stack.setCurrentIndex(idx)

        self._refresh_clip_rules_json_status()
        self._refresh_if_branch_json_status()

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
        elif op == "file_exists":
            self._if_left.setText(str(cond.get("path", cond.get("left", ""))))
        elif op == "window_exists":
            self._if_left.setText(
                str(cond.get("title_contains", cond.get("text", ""))),
            )

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
        elif op == "file_exists":
            cond["path"] = left
        elif op == "window_exists":
            cond["title_contains"] = left
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
        elif t == "pw_inner_text":
            params = {
                "into": self._pw_inner_into.text().strip(),
                "text": self._pw_inner_needle.text().strip(),
                "css": self._pw_inner_css.text().strip(),
                "nth": int(self._pw_inner_nth.value()),
                "exact": bool(self._pw_inner_exact_ck.isChecked()),
                "timeout_ms": int(self._pw_inner_timeout_ms.value()),
            }
            cdp_inner = self._pw_inner_cdp.text().strip()
            if cdp_inner:
                params["cdp_url"] = cdp_inner
        elif t == "set_variable":
            params = {
                "name": self._sv_name.text().strip(),
                "value": self._sv_val.text(),
            }
        elif t == "click_mouse":
            params = {
                "x": int(self._click_x.value()),
                "y": int(self._click_y.value()),
                "button": self._click_btn.currentText(),
            }
        elif t == "paste_clipboard":
            params = {}
        elif t == "read_clipboard":
            into_s = self._clip_into.text().strip()
            params = {
                "into": into_s if into_s else "_clipboard",
                "strip": bool(self._clip_strip.isChecked()),
            }
        elif t == "clear_clipboard":
            params = {}
        elif t == "clipboard_switch":
            rules_arr = json.loads(
                self._clip_rules_json.toPlainText().strip() or "[]",
            )
            if not isinstance(rules_arr, list):
                rules_arr = []
            params = {
                "variable": (
                    self._clip_switch_var.text().strip() or "_clipboard"
                ),
                "case_insensitive": bool(self._clip_switch_ci.isChecked()),
                "rules": rules_arr,
            }
        elif t == "note":
            params = {"text": self._note_text.text().strip()}
        elif t == "if":
            params = self._build_if_params()

        out: dict[str, Any] = {"id": sid, "type": t, "params": params}
        if name:
            out["name"] = name
        return out
