"""Graphical flow list editor (steps table + wiz-style step dialog)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rpa_assistant.app.models.common import FlowStatus
from rpa_assistant.app.models.flow import FlowRecord
from rpa_assistant.app.models.flow_dsl import validate_flow_definition
from rpa_assistant.app.storage.flow_repo import FlowRepository
from rpa_assistant.app.ui.flow.presentation import step_type_label, summarize_step
from rpa_assistant.app.ui.flow.step_dialog import StepEditorDialog


class FlowEditorPage(QWidget):
    def __init__(self, db_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db_path = Path(db_path)
        self._flows = FlowRepository(self._db_path)
        self._steps: list[dict] = []
        self._current: FlowRecord | None = None
        self._loading = False

        layout = QVBoxLayout(self)

        intro = QLabel(
            "通过表格管理自动化步骤。点击「添加步骤」选择动作类型；双击一行可修改。"
            "\n文本框中可写 ${列名}，执行时会换成 Excel 里对应单元格的值。",
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: palette(mid); padding: 4px 0;")
        layout.addWidget(intro)

        top = QHBoxLayout()
        top.addWidget(QLabel("流程"))
        self._flow_combo = QComboBox()
        self._flow_combo.setMinimumWidth(260)
        self._flow_combo.currentIndexChanged.connect(self._on_flow_selected)
        top.addWidget(self._flow_combo, stretch=1)
        self._btn_new_flow = QPushButton("新建流程")
        self._btn_new_flow.clicked.connect(self._on_new_flow)
        self._btn_save_flow = QPushButton("保存")
        self._btn_save_flow.clicked.connect(self._on_save_flow)
        self._btn_del_flow = QPushButton("删除流程")
        self._btn_del_flow.clicked.connect(self._on_delete_flow)
        self._btn_reload = QPushButton("刷新列表")
        self._btn_reload.clicked.connect(self._reload_flow_combo)
        top.addWidget(self._btn_new_flow)
        top.addWidget(self._btn_save_flow)
        top.addWidget(self._btn_del_flow)
        top.addWidget(self._btn_reload)
        layout.addLayout(top)

        meta = QGridLayout()
        meta.addWidget(QLabel("流程名称"), 0, 0)
        self._flow_name = QLineEdit()
        meta.addWidget(self._flow_name, 0, 1)
        meta.addWidget(QLabel("状态"), 1, 0)
        self._status_combo = QComboBox()
        for s in FlowStatus:
            self._status_combo.addItem(
                {"draft": "草稿", "active": "启用", "archived": "已归档"}.get(s.value, s.value),
                s.value,
            )
        meta.addWidget(self._status_combo, 1, 1)
        layout.addLayout(meta)

        step_box = QGroupBox("步骤列表")
        step_lay = QVBoxLayout(step_box)
        step_bar = QHBoxLayout()
        self._btn_add = QPushButton("添加步骤")
        self._btn_add.clicked.connect(self._on_add_step)
        self._btn_edit = QPushButton("编辑")
        self._btn_edit.clicked.connect(self._on_edit_step)
        self._btn_remove = QPushButton("删除")
        self._btn_remove.clicked.connect(self._on_remove_step)
        self._btn_up = QPushButton("上移")
        self._btn_up.clicked.connect(lambda: self._move_step(-1))
        self._btn_down = QPushButton("下移")
        self._btn_down.clicked.connect(lambda: self._move_step(1))
        for b in (self._btn_add, self._btn_edit, self._btn_remove, self._btn_up, self._btn_down):
            step_bar.addWidget(b)
        step_bar.addStretch(1)
        step_lay.addLayout(step_bar)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["顺序", "显示名称", "类型", "说明"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.doubleClicked.connect(lambda *_: self._on_edit_step())
        step_lay.addWidget(self._table)
        layout.addWidget(step_box, stretch=1)

        self._hint = QLabel("")
        self._hint.setWordWrap(True)
        layout.addWidget(self._hint)

        self._reload_flow_combo(select_last=False)

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
            self._flow_name.clear()
            self._refresh_table()
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
        raw = rec.definition.get("steps")
        self._steps = [dict(s) for s in raw] if isinstance(raw, list) else []
        self._refresh_table()
        self._hint.setText(f"已加载 {len(self._steps)} 个步骤。")

    def _refresh_table(self) -> None:
        self._table.setRowCount(len(self._steps))
        for i, step in enumerate(self._steps):
            t = step.get("type", "")
            name = str(step.get("name", "")).strip()
            self._table.setItem(i, 0, self._ro(str(i + 1)))
            self._table.setItem(i, 1, self._ro(name or "—"))
            self._table.setItem(i, 2, self._ro(step_type_label(t)))
            self._table.setItem(i, 3, self._ro(summarize_step(step)))

    def _ro(self, text: str) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        return it

    def _selected_row(self) -> int:
        indexes = self._table.selectedIndexes()
        if not indexes:
            return -1
        return indexes[0].row()

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
        definition = {"steps": self._steps}
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
        reply = QMessageBox.question(
            self,
            "删除流程",
            f"确定删除流程「{self._current.name}」？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        fid = self._current.id
        if self._flows.delete(fid):
            self._current = None
            self._steps = []
            self._reload_flow_combo()
            self._hint.setText("已删除。")

    def _on_add_step(self) -> None:
        dlg = StepEditorDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._steps.append(dlg.get_result())
        self._refresh_table()
        self._hint.setText("已添加一步，记得保存流程。")

    def _on_edit_step(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= len(self._steps):
            QMessageBox.information(self, "编辑", "请先选中一行步骤。")
            return
        dlg = StepEditorDialog(self, step=self._steps[row])
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._steps[row] = dlg.get_result()
        self._refresh_table()

    def _on_remove_step(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= len(self._steps):
            return
        del self._steps[row]
        self._refresh_table()

    def _move_step(self, delta: int) -> None:
        row = self._selected_row()
        if row < 0:
            return
        j = row + delta
        if j < 0 or j >= len(self._steps):
            return
        self._steps[row], self._steps[j] = self._steps[j], self._steps[row]
        self._refresh_table()
        self._table.selectRow(j)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._reload_flow_combo()
