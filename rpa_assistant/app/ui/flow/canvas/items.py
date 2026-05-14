"""Graphics items for the Alfred-style flow canvas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPolygonItem, QGraphicsRectItem
from PySide6.QtWidgets import QGraphicsSimpleTextItem

from rpa_assistant.app.ui.flow.presentation import step_type_label, summarize_step

if TYPE_CHECKING:
    from rpa_assistant.app.ui.flow.canvas.scene import FlowCanvasScene

_CARD_W = 200.0
_CARD_H = 86.0
_MERGE_SIZE = 88.0

_EDGE_Q = QColor("#4a5f72")
_FACE_Q = QColor("#161d26")
_CLIP_Q = QColor("#6b3eab")


def infer_canvas_kind(step: dict) -> str:
    meta = step.get("_canvas")
    if isinstance(meta, dict):
        kind = str(meta.get("kind", "")).strip().lower()
        if kind:
            return kind
    if str(step.get("name", "")).strip() == "汇入":
        return "merge"
    return "step"


class StepCardItem(QGraphicsRectItem):
    """Single runner step rendered as draggable rounded card."""

    def __init__(self, *, step_index: int, step: dict, scene_ref: FlowCanvasScene) -> None:
        super().__init__(0, 0, _CARD_W, _CARD_H)
        self._scene_ref = scene_ref
        self.step_id = str(step.get("id") or "").strip()

        self.step_index = step_index

        tint = QColor(
            _CLIP_Q if step.get("type") == "clipboard_switch" else _EDGE_Q,
        )
        lw = 1.85 if step.get("type") == "clipboard_switch" else 1.05
        self.setPen(QPen(tint.lighter(120), lw))
        self.setBrush(QBrush(QColor(_FACE_Q)))

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,
        )

        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

        inner = QRectF(self.rect()).adjusted(10, 8, -10, -8)

        lbl = step_type_label(str(step.get("type") or ""))
        nt = step.get("name")
        subtitle = summarize_step(step)
        if isinstance(subtitle, str) and len(subtitle) > 96:
            subtitle = subtitle[:93] + "…"

        self._lab_t = QGraphicsSimpleTextItem(self)
        self._lab_t.setText(lbl)
        font = self._lab_t.font()
        font.setPointSizeF(font.pointSizeF() + 1)
        font.setWeight(700)
        self._lab_t.setFont(font)
        self._lab_t.setBrush(QBrush(QColor("#eef2f7")))
        self._lab_t.setPos(inner.left(), inner.top())

        hint_raw = nt if isinstance(nt, str) else ""
        hint = hint_raw.strip() if hint_raw.strip() else f"#{step_index + 1}"

        self._lab_hint = QGraphicsSimpleTextItem(self)
        self._lab_hint.setText(hint[:48])
        self._lab_hint.setBrush(QBrush(QColor("#8390a3")))
        hfont = self._lab_hint.font()
        hfont.setPointSize(max(9, int(hfont.pointSize()) - 1))
        self._lab_hint.setFont(hfont)

        yt = inner.top()
        yt += font.pointSize() * 2.35
        self._lab_hint.setPos(inner.left(), yt)

        body = subtitle or ""
        self._lab_body = QGraphicsSimpleTextItem(self)
        self._lab_body.setText((body[:80] + ("…" if len(body) > 80 else "")) or "双击编辑")
        bf = self._lab_body.font()
        bf.setPointSize(max(9, int(bf.pointSize()) - 1))
        self._lab_body.setFont(bf)
        self._lab_body.setBrush(QBrush(QColor("#9aaab8")))
        yb = inner.bottom() - 22
        self._lab_body.setPos(inner.left(), yb)

    def itemChange(
        self,
        change: QGraphicsItem.GraphicsItemChange,
        value,
    ):
        try:
            if (
                change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
                and self.scene() is self._scene_ref
            ):
                self._scene_ref.schedule_edge_refresh()
        except Exception:
            pass
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None) -> None:
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        r = QRectF(self.rect())
        painter.drawRoundedRect(r, 10, 10)


class MergeDiamondItem(QGraphicsPolygonItem):
    """Visual merge — backed by runnable ``note`` + ``_canvas`` metadata."""

    def __init__(
        self,
        *,
        step: dict,
        step_index: int,
        scene_ref: FlowCanvasScene,
    ) -> None:
        cx = _MERGE_SIZE * 0.5
        poly = QPolygonF(
            [
                QPointF(cx, 4),
                QPointF(_MERGE_SIZE - 4, cx),
                QPointF(cx, _MERGE_SIZE - 4),
                QPointF(4, cx),
            ],
        )
        super().__init__(poly)

        self._scene_ref = scene_ref
        self.step_index = step_index
        self.step_id = str(step.get("id") or "").strip()

        pen_c = QColor("#34d399")
        self.setPen(QPen(pen_c.darker(115), 2))
        self.setBrush(QBrush(QColor("#12241c")))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,
        )
        lab = QGraphicsSimpleTextItem(self)
        lab.setBrush(QBrush(QColor("#aaf7e0")))
        lab.setText("汇入")
        br = lab.boundingRect()
        lab.setPos(cx - br.width() / 2, cx - br.height() / 2)

    def itemChange(
        self,
        change: QGraphicsItem.GraphicsItemChange,
        value,
    ):
        try:
            if (
                change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
                and self.scene() is self._scene_ref
            ):
                self._scene_ref.schedule_edge_refresh()
        except Exception:
            pass
        return super().itemChange(change, value)


class ClusterFrameItem(QGraphicsRectItem):
    """「Recorded block」圈选 — purely visual framing around cluster members."""

    def __init__(self, bounds: QRectF) -> None:
        pad = 14.0
        r = QRectF(bounds).adjusted(-pad, -pad, pad, pad)
        super().__init__(r)
        self.setZValue(-5)
        self.setPen(QPen(QColor("#5c6bff"), 1.35, Qt.PenStyle.DashLine))
        self.setBrush(QBrush(QColor.fromRgb(92, 107, 255, 42)))
