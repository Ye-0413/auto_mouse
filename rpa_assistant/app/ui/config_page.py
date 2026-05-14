from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from rpa_assistant.app.models.config import ConfigPayload, ConfigRecord
from rpa_assistant.app.storage.config_repo import ConfigRepository
from rpa_assistant.app.storage.flow_repo import FlowRepository

_logger = logging.getLogger(__name__)


class ConfigPage(QWidget):
    """Edit persisted configuration profiles (memory + automation defaults)."""

    def __init__(self, db_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db_path = Path(db_path)
        self._cfg = ConfigRepository(self._db_path)
        self._flows = FlowRepository(self._db_path)
        self._current_id: str | None = None
        self._loading = False

        layout = QVBoxLayout(self)
        self.setAccessibleName("全局配置档案")

        guide = QLabel(
            "<b>这一页保存「自动化常用选项」</b>：<br>"
            "① <b>使用的流程</b> — 与「运行」页默认勾选一致，也可在具体页面再选<br>"
            "② <b>超时、重试、失败截图</b> — 每次执行步骤时沿用这里的设置<br>"
            "③ 窗口标题与浏览器 CDP 供桌面 / 浏览器类步骤使用。",
        )
        guide.setWordWrap(True)
        guide.setOpenExternalLinks(False)
        guide.setStyleSheet(
            "background-color: rgba(255, 185, 95, 0.12);"
            "padding: 12px; border-radius: 10px;"
            "border: 1px solid rgba(230, 175, 110, 0.30);"
            "color: #d8cba8;",
        )
        layout.addWidget(guide)

        row = QHBoxLayout()
        row.addWidget(QLabel("当前配置档案"))
        self._profile_combo = QComboBox()
        self._profile_combo.setAccessibleName("当前配置档案")
        self._profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        row.addWidget(self._profile_combo, stretch=1)
        self._btn_new = QPushButton("新建")
        self._btn_new.clicked.connect(self._on_new_profile)
        self._btn_del = QPushButton("删除")
        self._btn_del.clicked.connect(self._on_delete_profile)
        self._btn_refresh = QPushButton("刷新")
        self._btn_refresh.clicked.connect(
            lambda: self._reload_profiles(select_default=False),
        )
        row.addWidget(self._btn_new)
        row.addWidget(self._btn_del)
        row.addWidget(self._btn_refresh)
        layout.addLayout(row)

        self._name_edit = QLineEdit()
        self._id_label = QLabel()
        self._id_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse,
        )
        self._default_check = QCheckBox("作为启动时使用的默认配置")
        meta = QFormLayout()
        meta.addRow("显示名称", self._name_edit)
        meta.addRow("配置 ID", self._id_label)
        meta.addRow(self._default_check)
        layout.addLayout(meta)

        flow_box = QGroupBox("流程")
        flow_form = QFormLayout(flow_box)
        self._flow_combo = QComboBox()
        self._flow_combo.setMinimumWidth(320)
        self._flow_combo.setAccessibleName("自动化默认使用的流程")
        flow_form.addRow("使用的流程", self._flow_combo)
        layout.addWidget(flow_box)

        win_box = QGroupBox("窗口与浏览器")
        win_form = QFormLayout(win_box)
        self._win_title = QLineEdit()
        self._browser_title = QLineEdit()
        self._cdp_url = QLineEdit()
        self._cdp_url.setPlaceholderText(
            "可选：Chrome DevTools Protocol 地址（如 Playwright 连接）",
        )
        win_form.addRow("目标窗口标题（包含匹配）", self._win_title)
        win_form.addRow("浏览器窗口标题", self._browser_title)
        win_form.addRow("browser_cdp_url", self._cdp_url)
        layout.addWidget(win_box)

        run_box = QGroupBox("执行参数")
        run_form = QFormLayout(run_box)
        self._timeout_ms = QSpinBox()
        self._timeout_ms.setRange(1_000, 3_600_000)
        self._timeout_ms.setSingleStep(1_000)
        self._retry = QSpinBox()
        self._retry.setRange(0, 99)
        self._shot_err = QCheckBox("失败时截图")
        run_form.addRow("默认超时（毫秒）", self._timeout_ms)
        run_form.addRow("失败重试次数", self._retry)
        run_form.addRow(self._shot_err)
        layout.addWidget(run_box)

        btn_row = QHBoxLayout()
        self._btn_save = QPushButton("保存")
        self._btn_save.setAccessibleName("保存配置")
        self._btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self._btn_save)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._reload_profiles(select_default=True)

    def focus_default(self) -> None:
        self._profile_combo.setFocus(Qt.FocusReason.TabFocusReason)

    def _reload_profiles(self, *, select_default: bool = False) -> None:
        """Reload profile combo; optionally select default or keep current id."""
        rows = self._cfg.list_all()
        if not rows:
            self._cfg.ensure_default()
            rows = self._cfg.list_all()

        self._loading = True
        self._profile_combo.blockSignals(True)
        self._profile_combo.clear()
        preferred_id = None
        if select_default:
            d = self._cfg.get_default()
            preferred_id = d.id if d else None
        elif self._current_id:
            preferred_id = self._current_id

        for r in rows:
            label = r.name
            if r.is_default:
                label += " ★"
            self._profile_combo.addItem(label, r.id)

        idx = 0
        if preferred_id:
            for i in range(self._profile_combo.count()):
                if self._profile_combo.itemData(i) == preferred_id:
                    idx = i
                    break
        self._profile_combo.setCurrentIndex(idx)
        self._profile_combo.blockSignals(False)
        self._loading = False
        self._on_profile_changed()

    def _on_profile_changed(self) -> None:
        if self._loading:
            return
        cid = self._profile_combo.currentData()
        if not cid:
            return
        rec = self._cfg.get(str(cid))
        if not rec:
            self._status.setText("配置已不存在，请刷新。")
            return
        self._current_id = rec.id
        self._fill_from_record(rec)
        self._reload_flow_combo()
        self._sync_flow_selection(rec.payload.flow_id)

    def _fill_from_record(self, rec: ConfigRecord) -> None:
        self._loading = True
        try:
            self._name_edit.setText(rec.name)
            self._id_label.setText(rec.id)
            self._default_check.setChecked(rec.is_default)

            p = rec.payload

            self._win_title.setText(p.target_window_title or "")
            self._browser_title.setText(p.target_browser_title or "")
            self._cdp_url.setText(p.browser_cdp_url or "")

            self._timeout_ms.setValue(int(p.default_timeout_ms))
            self._retry.setValue(int(p.default_retry_count))
            self._shot_err.setChecked(bool(p.screenshot_on_error))
        finally:
            self._loading = False

    def _reload_flow_combo(self) -> None:
        self._flow_combo.blockSignals(True)
        self._flow_combo.clear()
        self._flow_combo.addItem("（不选择）", "")
        try:
            for f in self._flows.list_all():
                self._flow_combo.addItem(f.name, f.id)
        except OSError as exc:
            _logger.warning("Flow list load failed: %s", exc)
        self._flow_combo.blockSignals(False)

    def _sync_flow_selection(self, flow_id: str | None) -> None:
        if not flow_id:
            self._flow_combo.setCurrentIndex(0)
            return
        idx = self._flow_combo.findData(flow_id)
        if idx >= 0:
            self._flow_combo.setCurrentIndex(idx)
        else:
            self._flow_combo.setCurrentIndex(0)

    def _collect_payload(self, base: ConfigPayload) -> ConfigPayload:
        flow_id = self._flow_combo.currentData()
        flow_s = str(flow_id) if flow_id else None

        return ConfigPayload(
            flow_id=flow_s,
            target_window_title=self._win_title.text().strip() or None,
            target_browser_title=self._browser_title.text().strip() or None,
            browser_cdp_url=self._cdp_url.text().strip() or None,
            default_timeout_ms=int(self._timeout_ms.value()),
            default_retry_count=int(self._retry.value()),
            screenshot_on_error=self._shot_err.isChecked(),
            extra=dict(base.extra),
        )

    def _on_save(self) -> None:
        if not self._current_id:
            self._status.setText("没有可选配置。")
            return
        rec = self._cfg.get(self._current_id)
        if not rec:
            self._status.setText("配置不存在。")
            return
        rec.name = self._name_edit.text().strip() or "未命名"
        rec.payload = self._collect_payload(rec.payload)
        rec.is_default = self._default_check.isChecked()
        self._cfg.save(rec)
        self._status.setText(f"已保存：{rec.name}")
        self._reload_profiles(select_default=bool(rec.is_default))

    def _on_new_profile(self) -> None:
        cid = self._cfg.create("新配置", ConfigPayload(), is_default=False)
        self._current_id = cid
        self._reload_profiles(select_default=False)
        idx = self._profile_combo.findData(cid)
        if idx >= 0:
            self._profile_combo.setCurrentIndex(idx)
        self._status.setText("已新建空白配置，请填写并保存。")

    def _on_delete_profile(self) -> None:
        rows = self._cfg.list_all()
        if len(rows) <= 1:
            QMessageBox.information(self, "删除", "至少需要保留一个配置档案。")
            return
        cid = self._current_id
        if not cid:
            return
        rec = self._cfg.get(cid)
        if not rec:
            return
        reply = QMessageBox.question(
            self,
            "删除配置",
            f"确定删除「{rec.name}」？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if rec.is_default:
            others = [r for r in rows if r.id != cid]
            if others:
                self._cfg.set_default(others[0].id)
        ok = self._cfg.delete(cid)
        if ok:
            self._status.setText("已删除。")
            self._reload_profiles(select_default=True)
        else:
            self._status.setText("删除失败。")

    def showEvent(self, event: QShowEvent) -> None:
        """Refresh flow list when the tab is shown."""
        super().showEvent(event)
        self._reload_flow_combo()
        if self._current_id:
            rec = self._cfg.get(self._current_id)
            if rec:
                self._sync_flow_selection(rec.payload.flow_id)
