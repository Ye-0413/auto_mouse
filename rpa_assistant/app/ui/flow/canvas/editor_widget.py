"""High-level QWidget: Alfred lane + autosave layout into definition."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from rpa_assistant.app.ui.flow.canvas.layout_state import (
    CANVAS_LAYOUT_KEY,
    normalize_canvas_layout,
    reorder_steps_from_layout,
)
from rpa_assistant.app.ui.flow.canvas.scene import FlowCanvasScene
from rpa_assistant.app.ui.flow.canvas.view import FlowGraphicsView


class FlowCanvasPane(QWidget):
    """Edits mutable ``steps`` + ``canvas_layout`` dict in-place."""

    canvas_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._steps: list[dict] | None = None
        self._layout_blob: dict | None = None
        self._edit_index: Callable[[int], None] | None = None
        self._on_key_edit: Callable[[int], None] | None = None
        self._on_key_delete: Callable[[int], None] | None = None

        outer = QVBoxLayout(self)

        banner = QLabel(
            "画布模式（Alfred 式横向链路）：拖拽卡片<strong>横向</strong>排版；"
            "松手静止约 <b>0.16s</b> 后按<strong>从左到右</strong>对齐执行顺序。"
            "<br>Ctrl + 滚轮缩放；双击卡片编辑该步骤。"
            "<br>「汇入」写成可跳过备注节点，画布以菱形渲染。",
        )
        banner.setWordWrap(True)
        banner.setTextFormat(Qt.TextFormat.RichText)
        banner.setAccessibleName("流程画布说明")
        banner.setAccessibleDescription(
            "拖拽卡片从左到右表示执行顺序。静止片刻后画布会重新对齐连接线。"
        )
        banner.setStyleSheet(
            "color:#a8b4c4;background:rgba(92,107,255,0.06);padding:10px;"
            "border-radius:10px;border:1px solid rgba(139,157,245,0.25);",
        )
        outer.addWidget(banner)

        bar = QHBoxLayout()
        self._btn_merge = QPushButton("添加汇入节点")
        self._btn_merge.setToolTip(
            f"插入画布汇入占位，位置写入 `{CANVAS_LAYOUT_KEY}`。"
        )
        self._btn_merge.clicked.connect(self._on_add_merge)
        hint = QLabel(
            f"<code>recorded_clusters</code>（JSON）可列出 step id，显示「录制块」虚线框。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#7d8c9c;font-size:12px")
        bar.addWidget(self._btn_merge)
        bar.addWidget(hint, stretch=1)
        outer.addLayout(bar)

        self._scene = FlowCanvasScene(
            on_schedule_finalize=self._on_geometry_activity,
        )
        self._view = FlowGraphicsView(
            on_double_click_lane_index=self._on_double_click,
            on_key=self._handle_canvas_key,
        )
        self._view.setScene(self._scene)
        self._view.setAccessibleName("流程画布视图")
        self._view.setAccessibleDescription(
            "左右方向键选中相邻步骤；按住 Control 并 Shift 加左右箭头与相邻步骤调换顺序。"
            "回车编辑；删除键移除当前选中步骤。"
        )
        self._view.setMinimumSize(QSize(520, 360))
        outer.addWidget(self._view, stretch=1)

        self._debouncer = QTimer(self)
        self._debouncer.setSingleShot(True)
        self._debouncer.timeout.connect(self._apply_canvas_idle)

    def set_edit_handler(self, fn: Callable[[int], None] | None) -> None:
        self._edit_index = fn

    def set_canvas_actions(
        self,
        *,
        on_edit_index: Callable[[int], None] | None = None,
        on_delete_index: Callable[[int], None] | None = None,
    ) -> None:
        self._on_key_edit = on_edit_index
        self._on_key_delete = on_delete_index

    def bind_state(self, steps: list[dict], canvas_layout: dict) -> None:
        self._steps = steps
        self._layout_blob = canvas_layout

    def reload_visuals(self) -> None:
        if self._steps is None or self._layout_blob is None:
            self._scene.clear_flow_items()
            return
        norm = normalize_canvas_layout(self._layout_blob, self._steps)
        positions = norm.get("positions")
        pmap = positions if isinstance(positions, dict) else {}
        typed_positions: dict[str, list[float]] = {}
        for k, v in pmap.items():
            if isinstance(k, str) and isinstance(v, (list, tuple)) and len(v) >= 2:
                try:
                    typed_positions[k] = [float(v[0]), float(v[1])]
                except (TypeError, ValueError):
                    continue
        rc = norm.get("recorded_clusters")
        clusters = rc if isinstance(rc, list) else []
        self._scene.rebuild(
            steps=self._steps,
            positions=typed_positions,
            recorded_clusters=clusters,
        )
        self._layout_blob.clear()
        self._layout_blob.update(norm)

    def flush_for_save(self) -> None:
        """Capture node positions + align step order with X before validate/save."""
        self._snapshot_positions_only()
        if self._steps is None or self._layout_blob is None:
            return
        norm = normalize_canvas_layout(self._layout_blob, self._steps)
        self._layout_blob.clear()
        self._layout_blob.update(norm)
        if reorder_steps_from_layout(self._steps, canvas_layout=self._layout_blob):
            self.reload_visuals()
            self.canvas_changed.emit()

    def _on_geometry_activity(self) -> None:
        self._scene.refresh_edges_only()
        self._debouncer.stop()
        self._debouncer.start(165)

    def _apply_canvas_idle(self) -> None:
        if self._steps is None or self._layout_blob is None:
            return
        self._snapshot_positions_only()
        norm = normalize_canvas_layout(self._layout_blob, self._steps)
        self._layout_blob.clear()
        self._layout_blob.update(norm)
        if reorder_steps_from_layout(self._steps, canvas_layout=self._layout_blob):
            self.reload_visuals()
            self.canvas_changed.emit()

    def _snapshot_positions_only(self) -> None:
        if self._steps is None or self._layout_blob is None:
            return
        pos = self._layout_blob.setdefault("positions", {})
        if not isinstance(pos, dict):
            return
        for it in self._scene.lane_items():
            sid = str(getattr(it, "step_id", "") or "").strip()
            if not sid:
                continue
            p = it.pos()
            pos[sid] = [float(p.x()), float(p.y())]

    def _on_double_click(self, index: int) -> None:
        if self._edit_index is not None:
            self._edit_index(index)

    def _handle_canvas_key(self, ev: QKeyEvent) -> bool:
        if self._steps is None:
            return False
        lane_n = len(self._steps)
        if lane_n <= 0:
            return False

        k = ev.key()
        mods = ev.modifiers()
        ctrl_shift = bool(
            mods & Qt.KeyboardModifier.ControlModifier
            and mods & Qt.KeyboardModifier.ShiftModifier,
        )

        sel = self._scene.selected_lane_index()

        if ctrl_shift and k in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            direction = -1 if k == Qt.Key.Key_Left else 1
            return self._swap_lane_with_neighbor(direction)

        if sel is None:
            return False

        if k == Qt.Key.Key_Left:
            nv = max(0, sel - 1)
            self._scene.set_selected_lane_index(nv)
            return True
        if k == Qt.Key.Key_Right:
            nv = min(lane_n - 1, sel + 1)
            self._scene.set_selected_lane_index(nv)
            return True

        if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            fn_edit = self._on_key_edit or self._edit_index
            if fn_edit is None:
                return False
            if sel < 0 or sel >= lane_n:
                return False
            fn_edit(sel)
            return True

        if k in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            fn_del = self._on_key_delete
            if fn_del is None:
                return False
            if sel < 0 or sel >= lane_n:
                return False
            fn_del(sel)
            return True

        return False

    def _repack_lane_x_positions(self) -> None:
        """Align stored X coords with current ``_steps`` order; preserve Y where known."""
        if self._steps is None or self._layout_blob is None:
            return
        pos = self._layout_blob.setdefault("positions", {})
        if not isinstance(pos, dict):
            return
        spacing = 224.0
        default_y = 48.0
        for i, step in enumerate(self._steps):
            sid = str(step.get("id") or "").strip()
            if not sid:
                continue
            xy = pos.get(sid)
            y = default_y
            if isinstance(xy, (list, tuple)) and len(xy) >= 2:
                try:
                    y = float(xy[1])
                except (TypeError, ValueError):
                    y = default_y
            pos[sid] = [float(i * spacing), y]

    def _swap_lane_with_neighbor(self, direction: int) -> bool:
        """Swap execution order with the adjacent lane; normalize horizontal spacing."""
        if self._steps is None or self._layout_blob is None:
            return False
        sel = self._scene.selected_lane_index()
        if sel is None:
            return False
        j = sel + direction
        if j < 0 or j >= len(self._steps):
            return False

        self._steps[sel], self._steps[j] = self._steps[j], self._steps[sel]
        self._repack_lane_x_positions()
        self.reload_visuals()
        self._scene.set_selected_lane_index(j)
        self.canvas_changed.emit()
        return True

    def current_selected_index(self) -> int | None:
        return self._scene.selected_lane_index()

    def _on_add_merge(self) -> None:
        if self._steps is None or self._layout_blob is None:
            return
        last_x = 0.0
        pos = self._layout_blob.setdefault("positions", {})
        if isinstance(pos, dict) and self._steps:
            for s in self._steps:
                sid = str(s.get("id") or "").strip()
                xy = pos.get(sid)
                if isinstance(xy, (list, tuple)) and len(xy) >= 1:
                    try:
                        last_x = max(last_x, float(xy[0]))
                    except (TypeError, ValueError):
                        pass
        nid = str(uuid.uuid4())
        self._steps.append(
            {
                "id": nid,
                "type": "note",
                "name": "汇入",
                "params": {"text": "画布汇入点（执行时跳过）"},
                "_canvas": {"kind": "merge"},
            },
        )
        pos[nid] = [last_x + 260.0, 48.0]
        self.reload_visuals()
        self.canvas_changed.emit()
