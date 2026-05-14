"""Zoom-friendly view for Alfred-style canvases."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QBrush, QColor, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QGraphicsView


class FlowGraphicsView(QGraphicsView):
    """Rubber-band select, Ctrl + wheel zoom, double-click lane node to edit."""

    def __init__(
        self,
        *,
        on_double_click_lane_index: Callable[[int], None],
        on_key: Callable[[QKeyEvent], bool] | None = None,
    ) -> None:
        super().__init__()
        self._on_dc = on_double_click_lane_index
        self._on_key = on_key

        bg = QColor("#0f141a")
        self.setBackgroundBrush(QBrush(bg))
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        fn = self._on_key
        if fn is not None and fn(event):
            event.accept()
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.08 if event.angleDelta().y() > 0 else 1 / 1.08
            self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseDoubleClickEvent(event)
            return
        pt = QPoint(
            round(event.position().x()),
            round(event.position().y()),
        ) if hasattr(event, "position") else event.pos()

        mapped = self.mapToScene(pt)
        sc = self.scene()
        if sc is None:
            super().mouseDoubleClickEvent(event)
            return
        for it in sc.items(mapped):
            idx = getattr(it, "step_index", None)
            if isinstance(idx, int):
                self._on_dc(idx)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)
