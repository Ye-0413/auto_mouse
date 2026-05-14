"""QGraphicsScene for horizontal Alfred lane + connectors."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainterPath
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsScene

from rpa_assistant.app.ui.flow.canvas.items import (
    ClusterFrameItem,
    MergeDiamondItem,
    StepCardItem,
    infer_canvas_kind,
)

_EDGE_COLOR = QColor("#4a6278")


class ConnectorSpline(QGraphicsPathItem):
    def __init__(self) -> None:
        super().__init__()
        self.setPen(_EDGE_COLOR.darker(110))
        self.setZValue(-2)


class FlowCanvasScene(QGraphicsScene):
    """Builds draggable nodes from ``steps`` + normalized ``positions``."""

    def __init__(
        self,
        *,
        on_schedule_finalize: Callable[[], None],
    ) -> None:
        super().__init__()
        self._on_schedule_finalize = on_schedule_finalize
        self._connectors: list[ConnectorSpline] = []
        self._node_lane: list[QGraphicsItem] = []

    def schedule_edge_refresh(self) -> None:
        self.refresh_edges_only()
        self._on_schedule_finalize()

    def clear_flow_items(self) -> None:
        for c in self._connectors:
            self.removeItem(c)
        self._connectors.clear()

        for it in list(self._node_lane):
            try:
                self.removeItem(it)
            except Exception:
                pass
        self._node_lane.clear()

        for it in list(self.items()):
            if isinstance(it, ClusterFrameItem):
                self.removeItem(it)

    def rebuild(
        self,
        *,
        steps: list[dict],
        positions: dict[str, list[float]],
        recorded_clusters: list,
    ) -> None:
        self.clear_flow_items()

        items_by_sid: dict[str, QGraphicsItem] = {}

        for idx, step in enumerate(steps):
            sid = str(step.get("id") or "").strip()
            xy = positions.get(sid)
            pos_x = float(xy[0]) if isinstance(xy, (list, tuple)) and len(xy) >= 2 else float(idx * 224)
            pos_y = float(xy[1]) if isinstance(xy, (list, tuple)) and len(xy) >= 2 else 48.0

            kin = infer_canvas_kind(step)
            if kin == "merge":
                it: QGraphicsItem = MergeDiamondItem(
                    step=step,
                    step_index=idx,
                    scene_ref=self,
                )
            else:
                it = StepCardItem(
                    step_index=idx,
                    step=step,
                    scene_ref=self,
                )
            self.addItem(it)
            it.setPos(pos_x, pos_y)
            self._node_lane.append(it)
            if sid:
                items_by_sid[sid] = it

        for _ in range(len(steps) - 1):
            edge = ConnectorSpline()
            self.addItem(edge)
            self._connectors.append(edge)

        self.refresh_edges_only()

        if isinstance(recorded_clusters, list):
            for cluster in recorded_clusters:
                if not isinstance(cluster, list) or len(cluster) < 2:
                    continue
                united: QRectF | None = None
                for cid in cluster:
                    if not isinstance(cid, str):
                        continue
                    wi = items_by_sid.get(cid)
                    if wi is None:
                        continue
                    br = wi.mapRectToScene(wi.boundingRect())
                    united = br if united is None else united.united(br)
                if united is not None:
                    rf = ClusterFrameItem(united)
                    self.addItem(rf)

        self._stretch_scene_rect()

    def refresh_edges_only(self) -> None:
        expected = max(0, len(self._node_lane) - 1)
        if len(self._connectors) != expected:
            return
        for i, conn in enumerate(self._connectors):
            src = self._node_lane[i]
            dst = self._node_lane[i + 1]
            conn.setPath(FlowCanvasScene._bezier_between(src, dst))

    @staticmethod
    def _center_right(it: QGraphicsItem) -> QPointF:
        r = it.mapRectToScene(it.boundingRect())
        return QPointF(r.right(), r.center().y())

    @staticmethod
    def _center_left(it: QGraphicsItem) -> QPointF:
        r = it.mapRectToScene(it.boundingRect())
        return QPointF(r.left(), r.center().y())

    @staticmethod
    def _bezier_between(a: QGraphicsItem, b: QGraphicsItem) -> QPainterPath:
        p0 = FlowCanvasScene._center_right(a)
        p3 = FlowCanvasScene._center_left(b)
        dx = max(54.0, (p3.x() - p0.x()) * 0.42)
        c1 = QPointF(p0.x() + dx, p0.y())
        c2 = QPointF(p3.x() - dx, p3.y())
        curve = QPainterPath(p0)
        curve.cubicTo(c1, c2, p3)
        return curve

    def _stretch_scene_rect(self) -> None:
        if not self.items():
            self.setSceneRect(QRectF(0, 0, 800, 360))
            return
        rr = QRectF()
        first = True
        for it in self.items():
            if isinstance(it, ConnectorSpline):
                continue
            r = it.mapRectToScene(it.boundingRect())
            if first:
                rr = r
                first = False
            else:
                rr = rr.united(r)
        pad = 64.0
        self.setSceneRect(rr.adjusted(-pad, -pad, pad * 3, pad * 3))

    def lane_items(self) -> list[QGraphicsItem]:
        return list(self._node_lane)

    def set_selected_lane_index(self, idx: int | None) -> None:
        """Single-select a lane card by execution index for keyboard UX."""
        for it in self._node_lane:
            try:
                it.setSelected(False)
            except Exception:
                continue
        if idx is None:
            return
        if idx < 0 or idx >= len(self._node_lane):
            return
        try:
            self._node_lane[idx].setSelected(True)
        except Exception:
            return

    def selected_lane_index(self) -> int | None:
        for it in self._node_lane:
            try:
                if it.isSelected():
                    idx = getattr(it, "step_index", None)
                    if isinstance(idx, int):
                        return idx
            except Exception:
                continue
        return None
