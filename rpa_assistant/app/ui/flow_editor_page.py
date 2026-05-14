"""Graphical flow editor (canvas-first, Alfred-style lane)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from rpa_assistant.app.models.common import FlowStatus
from rpa_assistant.app.models.flow import FlowRecord
from rpa_assistant.app.models.flow_dsl import validate_flow_definition
from rpa_assistant.app.storage.flow_repo import FlowRepository
from rpa_assistant.app.ui.flow.canvas import FlowCanvasPane
from rpa_assistant.app.ui.flow.canvas.layout_state import normalize_canvas_layout
from rpa_assistant.app.ui.flow.step_dialog import StepEditorDialog


def _summarize_step(step: dict) -> str:
    nm = str(step.get("name") or "").strip()
    if nm:
        return nm
    t = str(step.get("type") or "")
    sid = str(step.get("id") or "")[:8]
    return f"{t} [{sid}]" if sid else t


class FlowEditorPage(QWidget):
    def __init__(self, db_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db_path = Path(db_path)
        self._flows = FlowRepository(self._db_path)
        self._steps: list[dict] = []
        self._canvas_layout: dict[str, Any] = {}
        self._current: FlowRecord | None = None
        self._loading = False

        layout = QVBoxLayout(self)
        self.setAccessibleName("流程编辑")

        intro = QLabel(
            "流程顺序完全由<strong>画布</strong>决定：拖拽卡片从左到右即执行顺序。<br>"
            "双击卡片可编辑参数；在文字里写 <b>${变量名}</b>，运行时由上下文替换。<br>"
            "保存后请到「运行」页执行。",
        )
        intro.setWordWrap(True)
        intro.setOpenExternalLinks(False)
        intro.setStyleSheet(
            "background-color: rgba(175, 155, 235, 0.12);"
            "padding: 12px; border-radius: 10px;"
            "border: 1px solid rgba(190, 170, 235, 0.28);"
            "color: #d4cee8;",
        )
        layout.addWidget(intro)

        top = QHBoxLayout()
        top.addWidget(QLabel("流程"))
        self._flow_combo = QComboBox()
        self._flow_combo.setMinimumWidth(260)
        self._flow_combo.currentIndexChanged.connect(self._on_flow_selected)
        self._flow_combo.setAccessibleName("要编辑的流程")
        self._flow_combo.setAccessibleDescription("下拉列表中选择一条流程后在画布编排步骤顺序。")
        top.addWidget(self._flow_combo, stretch=1)
        self._btn_new_flow = QPushButton("新建流程")
        self._btn_new_flow.setAccessibleName("新建流程")
        self._btn_new_flow.clicked.connect(self._on_new_flow)
        self._btn_save_flow = QPushButton("保存")
        self._btn_save_flow.setAccessibleName("保存流程")
        self._btn_save_flow.setAccessibleDescription("将当前画布与表单内容写入数据库。")
        self._btn_save_flow.clicked.connect(self._on_save_flow)
        self._btn_del_flow = QPushButton("删除流程")
        self._btn_del_flow.setAccessibleName("删除流程")
        self._btn_del_flow.clicked.connect(self._on_delete_flow)
        self._btn_reload = QPushButton("刷新列表")
        self._btn_reload.setAccessibleName("刷新流程列表")
        self._btn_reload.clicked.connect(self._reload_flow_combo)
        top.addWidget(self._btn_new_flow)
        top.addWidget(self._btn_save_flow)
        top.addWidget(self._btn_del_flow)
        top.addWidget(self._btn_reload)
        layout.addLayout(top)

        meta = QGridLayout()
        meta.addWidget(QLabel("流程名称"), 0, 0)
        self._flow_name = QLineEdit()
        self._flow_name.setAccessibleName("流程显示名称")
        meta.addWidget(self._flow_name, 0, 1)
        meta.addWidget(QLabel("状态"), 1, 0)
        self._status_combo = QComboBox()
        self._status_combo.setAccessibleName("流程状态")
        for s in FlowStatus:
            self._status_combo.addItem(
                {"draft": "草稿", "active": "启用", "archived": "已归档"}.get(s.value, s.value),
                s.value,
            )
        meta.addWidget(self._status_combo, 1, 1)
        layout.addLayout(meta)

        step_box = QGroupBox("步骤操作（顺序请在画布中拖拽）")
        step_lay = QVBoxLayout(step_box)
        step_bar = QHBoxLayout()
        self._btn_add = QPushButton("添加步骤")
        self._btn_add.setAccessibleName("添加步骤")
        self._btn_add.clicked.connect(self._on_add_step)
        self._btn_edit = QPushButton("编辑")
        self._btn_edit.setAccessibleName("编辑选中步骤")
        self._btn_edit.setAccessibleDescription("编辑画布上当前选中的一张步骤卡片。")
        self._btn_edit.clicked.connect(self._on_edit_step)
        self._btn_remove = QPushButton("删除")
        self._btn_remove.setAccessibleName("删除选中步骤")
        self._btn_remove.clicked.connect(self._on_remove_step)
        for b in (self._btn_add, self._btn_edit, self._btn_remove):
            step_bar.addWidget(b)
        step_bar.addStretch(1)
        step_lay.addLayout(step_bar)
        layout.addWidget(step_box)

        self._canvas_pane = FlowCanvasPane(self)
        self._canvas_pane.set_edit_handler(self._on_canvas_edit_step)
        self._canvas_pane.set_canvas_actions(
            on_edit_index=self._on_canvas_edit_step,
            on_delete_index=self._on_delete_step_keyboard,
        )
        self._canvas_pane.canvas_changed.connect(self._on_canvas_changed)
        layout.addWidget(self._canvas_pane, stretch=1)

        self._hint = QLabel("")
        self._hint.setWordWrap(True)
        layout.addWidget(self._hint)

        self._canvas_pane.bind_state(self._steps, self._canvas_layout)
        self._reload_flow_combo(select_last=False)

    def focus_default(self) -> None:
        self._flow_combo.setFocus(Qt.FocusReason.TabFocusReason)

    def _touch_canvas_bindings(self) -> None:
        """Keep画布与当前 ``_steps``、``_canvas_layout``绑定并刷新场景。"""
        self._canvas_pane.bind_state(self._steps, self._canvas_layout)
        self._canvas_pane.reload_visuals()

    def _reload_flow_combo(self, *, select_last: bool = False) -> None:
        self._loading = True
        self._flow_combo.blockSignals(True)
        self._flow_combo.clear()
        rows = self._flows.list_all()
        keep_id = self._current.id if self._current else None
        for r in rows:
            label = f"{r.name} ({r.id[:8]}…)"
            self._flow_combo.addItem(label, r.id)
        self._flow_combo.blockSignals(False)
        self._loading = False

        if not rows:
            self._current = None
            self._steps = []
            self._canvas_layout = {}
            self._flow_name.clear()
            self._touch_canvas_bindings()
            self._hint.setText("暂无流程，请点击「新建流程」。")
            return

        idx = 0
        if keep_id:
            for i in range(self._flow_combo.count()):
                if self._flow_combo.itemData(i) == keep_id:
                    idx = i
                    break
        elif select_last:
            idx = self._flow_combo.count() - 1
        self._flow_combo.setCurrentIndex(idx)
        self._on_flow_selected()

    def _on_flow_selected(self) -> None:
        if self._loading:
            return
        fid = self._flow_combo.currentData()
        if not fid:
            return
        rec = self._flows.get(str(fid))
        if not rec:
            self._hint.setText("流程不存在，请刷新。")
            return
        self._current = rec
        self._flow_name.setText(rec.name)
        si = self._status_combo.findData(rec.status.value)
        self._status_combo.setCurrentIndex(max(0, si))
        defn = rec.definition if isinstance(rec.definition, dict) else {}
        raw = defn.get("steps")
        self._steps = [dict(s) for s in raw] if isinstance(raw, list) else []
        raw_canvas = defn.get("canvas_layout")
        self._canvas_layout = dict(raw_canvas) if isinstance(raw_canvas, dict) else {}
        self._touch_canvas_bindings()
        self._hint.setText(f"已加载 {len(self._steps)} 个步骤。")

    def _on_canvas_changed(self) -> None:
        self._hint.setText(f"画布已更新，当前 {len(self._steps)} 步。")

    def _on_new_flow(self) -> None:
        fid = self._flows.create("新流程", {"steps": []}, status=FlowStatus.DRAFT)
        self._reload_flow_combo(select_last=True)
        idx = self._flow_combo.findData(fid)
        if idx >= 0:
            self._flow_combo.setCurrentIndex(idx)
        self._hint.setText("已新建流程，请添加步骤后点击保存。")

    def _on_save_flow(self) -> None:
        if not self._current:
            return
        name = self._flow_name.text().strip() or "未命名流程"
        st = FlowStatus(str(self._status_combo.currentData()))
        self._canvas_pane.flush_for_save()
        merged_canvas = normalize_canvas_layout(self._canvas_layout, self._steps)
        self._canvas_layout.clear()
        self._canvas_layout.update(merged_canvas)
        definition = dict(self._current.definition or {})
        definition["steps"] = self._steps
        definition["canvas_layout"] = merged_canvas
        errs = validate_flow_definition(definition)
        if errs:
            QMessageBox.warning(self, "无法保存", "\n".join(errs[:12]))
            return
        self._current.name = name
        self._current.definition = definition
        self._current.status = st
        self._flows.save(self._current)
        self._hint.setText(f"已保存「{name}」。")
        self._reload_flow_combo()

    def _on_delete_flow(self) -> None:
        if not self._current:
            return
        n_steps = len(self._steps)
        reply = QMessageBox.question(
            self,
            "删除流程",
            f"确定删除流程「{self._current.name}」及其全部 {n_steps} 个步骤？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        fid = self._current.id
        if self._flows.delete(fid):
            self._current = None
            self._steps = []
            self._canvas_layout = {}
            self._reload_flow_combo()
            self._hint.setText("已删除。")

    def _on_add_step(self) -> None:
        dlg = StepEditorDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._steps.append(dlg.get_result())
        self._touch_canvas_bindings()
        self._hint.setText("已添加一步，记得保存流程。")

    def _selected_step_index(self) -> int:
        idx = self._canvas_pane.current_selected_index()
        return idx if isinstance(idx, int) else -1

    def _on_edit_step(self) -> None:
        row = self._selected_step_index()
        if row < 0 or row >= len(self._steps):
            QMessageBox.information(self, "编辑", "请先在画布中点选一个步骤卡片。")
            return
        dlg = StepEditorDialog(self, step=self._steps[row])
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._steps[row] = dlg.get_result()
        self._touch_canvas_bindings()

    def _on_canvas_edit_step(self, row: int) -> None:
        if row < 0 or row >= len(self._steps):
            return
        dlg = StepEditorDialog(self, step=self._steps[row])
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._steps[row] = dlg.get_result()
        self._touch_canvas_bindings()

    def _on_remove_step(self) -> None:
        row = self._selected_step_index()
        if row < 0 or row >= len(self._steps):
            QMessageBox.information(self, "删除步骤", "请先在画布中点选一张步骤卡片。")
            return
        self._maybe_remove_step_at(row)

    def _maybe_remove_step_at(self, row: int) -> None:
        if row < 0 or row >= len(self._steps):
            return
        step = self._steps[row]
        label = _summarize_step(step)
        reply = QMessageBox.question(
            self,
            "删除步骤",
            f"将从流程中移除步骤「{label}」（画布第 {row + 1} 张）。删除后请先保存流程。确定？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        del self._steps[row]
        self._touch_canvas_bindings()

    def _on_delete_step_keyboard(self, row: int) -> None:
        if row < 0 or row >= len(self._steps):
            return
        self._maybe_remove_step_at(row)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._reload_flow_combo()
