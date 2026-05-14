from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

from rpa_assistant.app.excel.mapper import build_variable_map_default
from rpa_assistant.app.excel.reader import load_sheet_snapshot, open_workbook_meta
from rpa_assistant.app.excel.validator import validate_rows
from rpa_assistant.app.excel.results_export import export_executions_to_xlsx
from rpa_assistant.app.models.config import ConfigPayload, ConfigRecord
from rpa_assistant.app.models.flow_dsl import validate_flow_definition
from rpa_assistant.paths import ensure_app_dirs
from rpa_assistant.app.storage.config_repo import ConfigRepository
from rpa_assistant.app.storage.execution_repo import ExecutionRepository
from rpa_assistant.app.storage.flow_repo import FlowRepository
from rpa_assistant.app.ui.workers.batch_worker import BatchRunWorker

_logger = logging.getLogger(__name__)


class ExcelPreviewPage(QWidget):
    """Load Excel sheets, preview rows, map columns to variables, persist to config."""

    def __init__(self, db_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db_path = Path(db_path)
        self._repo = ConfigRepository(self._db_path)
        self._flows = FlowRepository(self._db_path)
        self._current_file: Path | None = None
        self._config: ConfigRecord | None = None
        self._last_headers: list[str] = []
        self._last_preview_rows: list[list[str]] = []
        self._last_data_row_count: int = 0
        self._worker: BatchRunWorker | None = None
        self._last_batch_id: str | None = None

        root = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self._btn_open = QPushButton("选择 Excel…")
        self._btn_open.clicked.connect(self._on_choose_file)
        self._path_label = QLabel("未选择文件")
        self._path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse,
        )
        toolbar.addWidget(self._btn_open)
        toolbar.addWidget(self._path_label, stretch=1)
        root.addLayout(toolbar)

        form = QFormLayout()
        self._sheet_combo = QComboBox()
        self._header_spin = QSpinBox()
        self._header_spin.setMinimum(1)
        self._header_spin.setMaximum(1_048_576)
        self._header_spin.setValue(1)

        self._pk_combo = QComboBox()
        form.addRow("工作表", self._sheet_combo)
        form.addRow("表头所在行（从 1 开始）", self._header_spin)
        form.addRow("主键列（可选）", self._pk_combo)
        self._sheet_combo.currentTextChanged.connect(lambda _: self._on_reload())
        self._header_spin.valueChanged.connect(lambda _: self._on_reload())
        root.addLayout(form)

        btn_row = QHBoxLayout()
        self._btn_reload = QPushButton("重新加载")
        self._btn_reload.clicked.connect(self._on_reload)
        self._btn_validate = QPushButton("校验预览行")
        self._btn_validate.clicked.connect(self._on_validate)
        self._btn_save = QPushButton("保存到默认配置")
        self._btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self._btn_reload)
        btn_row.addWidget(self._btn_validate)
        btn_row.addWidget(self._btn_save)
        self._btn_run_first = QPushButton("试运行首行")
        self._btn_run_first.setToolTip("使用配置中绑定的流程，仅对当前预览的第一行数据执行一次")
        self._btn_run_first.clicked.connect(self._on_run_first_row)
        self._btn_run_preview = QPushButton("执行已勾选预览行")
        self._btn_run_preview.setToolTip(
            "仅对预览表中勾选「执行」的行依次运行流程（预览最多显示 500 行）",
        )
        self._btn_run_preview.clicked.connect(self._on_run_all_preview)
        self._btn_run_full = QPushButton("执行整张表")
        self._btn_run_full.setToolTip(
            "在后台线程读取整张工作表的全部数据行并依次执行（不限于 500 行预览）",
        )
        self._btn_run_full.clicked.connect(self._on_run_full_sheet)
        self._btn_stop = QPushButton("停止")
        self._btn_stop.setToolTip(
            "请求停止：在处理下一行数据之前结束批量（当前行仍会执行完）。",
        )
        self._btn_stop.clicked.connect(self._on_stop_batch)
        self._btn_stop.setEnabled(False)
        self._btn_pause = QPushButton("暂停")
        self._btn_pause.setToolTip(
            "在已开始下一行前暂停；当前正在跑的数据行会执行完后再停住。",
        )
        self._btn_pause.clicked.connect(self._on_pause_batch)
        self._btn_pause.setEnabled(False)
        self._btn_resume = QPushButton("继续")
        self._btn_resume.setToolTip("从暂停处继续批量。")
        self._btn_resume.clicked.connect(self._on_resume_batch)
        self._btn_resume.setEnabled(False)
        self._btn_check_all_rows = QPushButton("勾选全部预览行")
        self._btn_check_all_rows.clicked.connect(lambda: self._set_all_preview_run_checks(True))
        self._btn_check_no_rows = QPushButton("取消全部勾选")
        self._btn_check_no_rows.clicked.connect(lambda: self._set_all_preview_run_checks(False))
        self._btn_export_batch = QPushButton("导出最近一批结果为 Excel…")
        self._btn_export_batch.clicked.connect(self._on_export_last_batch)
        btn_row.addWidget(self._btn_run_first)
        btn_row.addWidget(self._btn_run_preview)
        btn_row.addWidget(self._btn_run_full)
        btn_row.addWidget(self._btn_stop)
        btn_row.addWidget(self._btn_pause)
        btn_row.addWidget(self._btn_resume)
        btn_row.addWidget(self._btn_check_all_rows)
        btn_row.addWidget(self._btn_check_no_rows)
        btn_row.addWidget(self._btn_export_batch)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        preview_box = QGroupBox("数据预览（最多 500 行）")
        preview_layout = QVBoxLayout(preview_box)
        self._preview = QTableWidget(0, 0)
        self._preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._preview.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive,
        )
        preview_layout.addWidget(self._preview)
        root.addWidget(preview_box, stretch=2)

        map_box = QGroupBox("列映射（启用 / Excel 列名 / 变量名）")
        map_layout = QVBoxLayout(map_box)
        self._mapping = QTableWidget(0, 3)
        self._mapping.setHorizontalHeaderLabels(["启用", "Excel 列", "变量名"])
        self._mapping.horizontalHeader().setStretchLastSection(True)
        map_layout.addWidget(self._mapping)
        root.addWidget(map_box, stretch=1)

        self._status = QLabel("就绪")
        self._status.setWordWrap(True)
        root.addWidget(self._status)

        log_box = QGroupBox("执行输出（最近一轮）")
        log_lay = QVBoxLayout(log_box)
        self._run_log = QTextEdit()
        self._run_log.setReadOnly(True)
        self._run_log.setMinimumHeight(120)
        self._run_log.setPlaceholderText("运行批量执行后，这里会显示步骤日志……")
        log_lay.addWidget(self._run_log)
        root.addWidget(log_box)

        self._on_bootstrap()

    def _on_bootstrap(self) -> None:
        try:
            self._config = self._repo.ensure_default()
            self._hydrate_from_config(self._config)
        except OSError as exc:
            _logger.exception("Failed to load config")
            self._status.setText(f"配置加载失败：{exc}")

    def _hydrate_from_config(self, record: ConfigRecord) -> None:
        p = record.payload
        path_str = p.excel_file_path
        if not path_str:
            return
        candidate = Path(path_str).expanduser()
        if not candidate.is_file():
            self._status.setText(f"上次路径不存在，请重新选择：{candidate}")
            return
        self._current_file = candidate.resolve()
        self._path_label.setText(str(self._current_file))
        try:
            sheets = open_workbook_meta(self._current_file)
        except OSError as exc:
            self._status.setText(f"无法读取工作簿：{exc}")
            return
        self._sheet_combo.blockSignals(True)
        self._sheet_combo.clear()
        self._sheet_combo.addItems(sheets)
        sheet = p.excel_sheet_name or (sheets[0] if sheets else "")
        idx = self._sheet_combo.findText(sheet)
        if idx >= 0:
            self._sheet_combo.setCurrentIndex(idx)
        self._sheet_combo.blockSignals(False)
        self._header_spin.setValue(max(1, int(p.excel_header_row or 1)))
        self._on_reload()

    def _on_choose_file(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "选择 Excel 文件",
            "",
            "Excel 工作簿 (*.xlsx *.xlsm);;所有文件 (*.*)",
        )
        if not path_str:
            return
        path = Path(path_str).expanduser().resolve()
        self._current_file = path
        self._path_label.setText(str(path))
        try:
            sheets = open_workbook_meta(path)
        except OSError as exc:
            QMessageBox.warning(self, "读取失败", str(exc))
            return
        self._sheet_combo.blockSignals(True)
        self._sheet_combo.clear()
        self._sheet_combo.addItems(sheets)
        if sheets:
            self._sheet_combo.setCurrentIndex(0)
        self._sheet_combo.blockSignals(False)
        self._on_reload()

    def _active_sheet_name(self) -> str:
        return self._sheet_combo.currentText()

    def _on_reload(self) -> None:
        if not self._current_file:
            self._status.setText("请先选择 Excel 文件。")
            return
        sheet = self._active_sheet_name()
        if not sheet:
            self._status.setText("工作簿中没有可用工作表。")
            return
        try:
            snap = load_sheet_snapshot(
                self._current_file,
                sheet,
                header_row_1based=self._header_spin.value(),
            )
        except (OSError, ValueError) as exc:
            self._status.setText(f"加载失败：{exc}")
            _logger.exception("Excel load failed")
            return

        self._fill_preview(snap)

        self._last_headers = list(snap.headers)
        self._last_preview_rows = [list(r) for r in snap.preview_rows]
        self._last_data_row_count = int(snap.data_row_count)

        payload = self._config.payload if self._config else ConfigPayload()
        self._fill_mapping_table(snap, payload)
        self._fill_pk_combo(snap.headers, payload.excel_primary_key_column)

        tip = f"已加载 {snap.data_row_count} 行数据；预览 {len(snap.preview_rows)} 行"
        if snap.truncated_preview:
            tip += "（预览已截断为前 500 行）"
        self._status.setText(tip)

    def _fill_preview(self, snap) -> None:
        self._preview.clear()
        headers = snap.headers
        hdr = ["执行", "状态"] + list(headers)
        self._preview.setColumnCount(len(hdr))
        self._preview.setHorizontalHeaderLabels(hdr)
        self._preview.setRowCount(len(snap.preview_rows))
        for r_i, row in enumerate(snap.preview_rows):
            chk = QTableWidgetItem()
            chk.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable,
            )
            chk.setCheckState(Qt.CheckState.Checked)
            self._preview.setItem(r_i, 0, chk)

            stat = QTableWidgetItem("—")
            stat.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self._preview.setItem(r_i, 1, stat)

            for c_i, val in enumerate(row):
                item = QTableWidgetItem(val)
                self._preview.setItem(r_i, c_i + 2, item)

    def _fill_pk_combo(self, headers: list[str], current: str | None) -> None:
        self._pk_combo.blockSignals(True)
        self._pk_combo.clear()
        self._pk_combo.addItem("", "")
        for h in headers:
            if not str(h).strip():
                continue
            self._pk_combo.addItem(h, h)
        if current:
            idx = self._pk_combo.findData(current)
            if idx >= 0:
                self._pk_combo.setCurrentIndex(idx)
        self._pk_combo.blockSignals(False)

    def _fill_mapping_table(self, snap, payload: ConfigPayload) -> None:
        headers = snap.headers
        defaults = build_variable_map_default([h for h in headers if str(h).strip()])
        saved_map = payload.excel_variable_map or {}
        selected = set(payload.excel_selected_columns or [])
        self._mapping.setRowCount(len(headers))
        for i, col_name in enumerate(headers):
            key = str(col_name).strip()
            var_name = saved_map.get(key, defaults.get(key, key))
            if not selected and saved_map:
                checked = bool(var_name)
            elif selected:
                checked = key in selected
            else:
                checked = bool(key)

            check = QTableWidgetItem()
            check.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable,
            )
            check.setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked,
            )
            self._mapping.setItem(i, 0, check)

            name_item = QTableWidgetItem(key)
            name_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self._mapping.setItem(i, 1, name_item)

            var_item = QTableWidgetItem(var_name)
            self._mapping.setItem(i, 2, var_item)

    def _collect_mapping(self) -> tuple[list[str], dict[str, str]]:
        enabled: list[str] = []
        var_map: dict[str, str] = {}
        for row in range(self._mapping.rowCount()):
            check = self._mapping.item(row, 0)
            name_item = self._mapping.item(row, 1)
            var_item = self._mapping.item(row, 2)
            if not name_item:
                continue
            col_name = name_item.text().strip()
            if not col_name:
                continue
            var_name = (var_item.text() if var_item else "").strip()
            if check and check.checkState() == Qt.CheckState.Checked:
                enabled.append(col_name)
                if var_name:
                    var_map[col_name] = var_name
        return enabled, var_map

    def _collect_payload_merge(self, base: ConfigPayload) -> ConfigPayload:
        if not self._current_file:
            return base
        primary = self._pk_combo.currentData()
        primary = primary if primary else None
        enabled, var_map = self._collect_mapping()
        return ConfigPayload(
            excel_file_path=str(self._current_file),
            excel_sheet_name=self._active_sheet_name(),
            excel_header_row=int(self._header_spin.value()),
            excel_selected_columns=enabled,
            excel_variable_map=var_map,
            excel_primary_key_column=primary,
            excel_mapping_id=base.excel_mapping_id,
            flow_id=base.flow_id,
            target_browser_title=base.target_browser_title,
            target_window_title=base.target_window_title,
            browser_cdp_url=base.browser_cdp_url,
            default_timeout_ms=base.default_timeout_ms,
            default_retry_count=base.default_retry_count,
            screenshot_on_error=base.screenshot_on_error,
            extra=dict(base.extra),
        )

    def _preview_row_cells(self, preview_row: int) -> list[str]:
        """Data cells only (no run/status/meta columns)."""
        out: list[str] = []
        for col in range(2, self._preview.columnCount()):
            cell = self._preview.item(preview_row, col)
            out.append(cell.text() if cell else "")
        return out

    def _set_all_preview_run_checks(self, checked: bool) -> None:
        st = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self._preview.rowCount()):
            chk = self._preview.item(row, 0)
            if chk and chk.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                chk.setCheckState(st)

    def _selected_preview_pairs(self) -> list[tuple[int, list[str]]]:
        pairs: list[tuple[int, list[str]]] = []
        for row in range(self._preview.rowCount()):
            chk = self._preview.item(row, 0)
            if not chk or chk.checkState() != Qt.CheckState.Checked:
                continue
            pairs.append((row, self._preview_row_cells(row)))
        return pairs

    def _on_pause_batch(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.request_pause()
            cur = self._status.text().split("\n")[0]
            self._status.setText(
                cur + "\n↳ 已请求暂停：当前数据行仍会跑完；下一行前会停住直至点「继续」。",
            )

    def _on_resume_batch(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.request_resume()

    def _on_export_last_batch(self) -> None:
        bid = self._last_batch_id
        if not bid:
            QMessageBox.information(self, "", "暂无已完成的批量 ID，请先跑一次批量后再导出。")
            return
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "导出结果为 Excel",
            "",
            "Excel 工作簿 (*.xlsx)",
        )
        if not path_str:
            return
        path = Path(path_str).expanduser()
        if path.suffix.lower() != ".xlsx":
            path = path.with_suffix(".xlsx")
        try:
            rows = ExecutionRepository(self._db_path).list_by_batch(bid)
            if not rows:
                QMessageBox.information(self, "", "找不到该批次下的执行记录。")
                return
            export_executions_to_xlsx(rows, path)
        except OSError as exc:
            QMessageBox.warning(self, "导出失败", str(exc))
            return
        QMessageBox.information(self, "完成", f"已导出 {len(rows)} 条记录。\n{path}")

    def _on_row_started_ui(self, preview_ix: object) -> None:
        if not isinstance(preview_ix, int) or preview_ix < 0:
            return
        it = self._preview.item(preview_ix, 1)
        if it:
            it.setText("执行中…")
            it.setForeground(QColor(Qt.GlobalColor.darkYellow))

    def _on_row_finished_ui(
        self,
        preview_ix: object,
        label: str,
        ok_row: bool,
    ) -> None:
        if not isinstance(preview_ix, int) or preview_ix < 0:
            return
        cell = self._preview.item(preview_ix, 1)
        if cell:
            cell.setText(label)
            cell.setForeground(
                QColor(Qt.GlobalColor.darkGreen)
                if ok_row
                else QColor(Qt.GlobalColor.darkRed),
            )

    def _on_validate(self) -> None:
        if not self._current_file:
            QMessageBox.information(self, "校验", "请先选择并加载 Excel。")
            return
        sheet = self._active_sheet_name()
        if not sheet:
            return
        try:
            snap = load_sheet_snapshot(
                self._current_file,
                sheet,
                header_row_1based=self._header_spin.value(),
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "校验", str(exc))
            return
        enabled, _ = self._collect_mapping()
        pk = self._pk_combo.currentData()
        pk = pk if pk else None
        issues = validate_rows(
            snap.headers,
            snap.preview_rows,
            primary_key_header=pk,
            mapped_columns=enabled or None,
        )
        if not issues:
            QMessageBox.information(self, "校验", "预览范围内未发现问题。")
            return
        lines = []
        for iss in issues[:30]:
            lines.append(
                f"第 {iss.data_row_index} 行：" + "；".join(iss.messages),
            )
        extra = ""
        if len(issues) > 30:
            extra = f"\n… 共 {len(issues)} 行存在问题"
        QMessageBox.warning(self, "校验", "\n".join(lines) + extra)

    def _on_save(self) -> None:
        if not self._current_file:
            QMessageBox.information(self, "保存", "请先选择 Excel 文件。")
            return
        record = self._repo.ensure_default()
        payload = self._collect_payload_merge(record.payload)
        record.payload = payload
        self._repo.save(record)
        self._config = record
        self._status.setText(
            f"已写入默认配置（{record.id}）：{self._current_file.name}",
        )

    def _set_batch_ui_idle(self, idle: bool) -> None:
        self._btn_run_first.setEnabled(idle)
        self._btn_run_preview.setEnabled(idle)
        self._btn_run_full.setEnabled(idle)
        self._btn_stop.setEnabled(not idle)
        self._btn_pause.setEnabled(not idle)
        self._btn_resume.setEnabled(not idle)

    def _on_stop_batch(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.request_cancel()

    def _on_worker_done(
        self,
        ok: int,
        fail: int,
        err: str,
        cancelled: bool,
        batch_id: str,
    ) -> None:
        self._set_batch_ui_idle(True)
        self._worker = None
        if batch_id.strip():
            self._last_batch_id = batch_id
        if err:
            QMessageBox.warning(self, "执行异常", err)
            return
        if cancelled:
            self._status.setText(f"已停止：成功 {ok} 行，失败 {fail} 行")
            QMessageBox.information(
                self,
                "已停止",
                f"成功 {ok} 行，失败 {fail} 行；后续数据行未执行。",
            )
            return
        QMessageBox.information(self, "完成", f"成功 {ok} 行，失败 {fail} 行。")
        self._status.setText(f"最近批量：成功 {ok}，失败 {fail}（可导出结果为 Excel）")

    def _start_worker(
        self,
        labeled_preview_rows: list[tuple[int, list[str]]] | None = None,
        *,
        load_full_sheet: bool = False,
    ) -> None:
        cfg = self._repo.ensure_default()
        p = cfg.payload
        if not p.flow_id:
            QMessageBox.warning(
                self,
                "未绑定流程",
                "请先在「配置」页为当前配置选择要执行的流程。",
            )
            return
        flow = self._flows.get(p.flow_id)
        if not flow:
            QMessageBox.warning(
                self,
                "",
                "找不到配置中绑定的流程，请刷新或重新选择。",
            )
            return
        steps = flow.definition.get("steps")
        if not isinstance(steps, list) or not steps:
            QMessageBox.warning(
                self,
                "",
                "流程中没有步骤，请先到「流程」页编辑。",
            )
            return
        errs = validate_flow_definition(flow.definition)
        if errs:
            QMessageBox.warning(self, "流程无效", "\n".join(errs[:10]))
            return
        _, var_map = self._collect_mapping()
        if not self._last_headers:
            QMessageBox.warning(
                self,
                "",
                "请先点击「重新加载」以确保预览已就绪。",
            )
            return

        if self._worker and self._worker.isRunning():
            return

        ui_ix: list[int] | None = None
        data_rows_arg: list[list[str]] = []

        if load_full_sheet:
            if self._last_data_row_count <= 0:
                QMessageBox.information(
                    self,
                    "",
                    "当前工作表没有数据行可执行，请确认表头行号与内容。",
                )
                return
            n = self._last_data_row_count
            hint = ""
            pv = len(self._last_preview_rows)
            if n > pv:
                hint = (
                    f"\n\n说明：表格预览最多 {pv} 行，整表约 {n} 行"
                    f"{ '（预览已截断）' if pv >= 500 else '' }。"
                )
            tail = f"约 {n} 行数据。"
            if n > 200:
                tail += " 数据量较大，耗时可能较长。"
            reply = QMessageBox.question(
                self,
                "执行整张表",
                "将从磁盘完整读取当前工作表的数据行并在后台依次执行。"
                + "预览中的「勾选/状态」列仅用于预览模式下的筛选，不参与整表跑批。"
                f"{hint}\n\n{tail}\n\n是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        else:
            if not labeled_preview_rows:
                QMessageBox.information(self, "", "没有勾选任何预览行可供执行。")
                return
            data_rows_arg = [r for _, r in labeled_preview_rows]
            ui_ix = [idx for idx, _ in labeled_preview_rows]
            n = len(data_rows_arg)
            if n > 200:
                reply = QMessageBox.question(
                    self,
                    "确认",
                    f"即将执行勾选的数据行（共 {n} 行），是否继续？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

        self._set_batch_ui_idle(False)
        self._run_log.clear()
        if not load_full_sheet and ui_ix is not None:
            for row_i in ui_ix:
                st_cell = self._preview.item(row_i, 1)
                if st_cell:
                    st_cell.setText("待执行")
                    st_cell.setForeground(QColor(Qt.GlobalColor.darkGray))
        _, _, _, shots = ensure_app_dirs()
        cdp = (p.browser_cdp_url or "").strip() or None
        self._worker = BatchRunWorker(
            self._db_path,
            steps=list(steps),
            headers=self._last_headers,
            data_rows=data_rows_arg,
            variable_map=var_map,
            config_id=cfg.id,
            flow_id=p.flow_id,
            excel_path=self._current_file,
            sheet_name=self._active_sheet_name(),
            header_row_1based=int(self._header_spin.value()),
            load_full_sheet=load_full_sheet,
            screenshot_on_error=bool(p.screenshot_on_error),
            screenshots_dir=shots,
            browser_cdp_url=cdp,
            ui_preview_indices=ui_ix,
            parent=self,
        )
        self._worker.log_line.connect(self._run_log.append)
        self._worker.row_started_signal.connect(self._on_row_started_ui)
        self._worker.row_finished_signal.connect(self._on_row_finished_ui)
        self._worker.finished_counts.connect(self._on_worker_done)
        self._worker.start()

    def _on_run_first_row(self) -> None:
        if not self._last_preview_rows:
            QMessageBox.information(self, "", "没有可执行的预览行，请先加载 Excel。")
            return
        chk = self._preview.item(0, 0)
        if chk and chk.checkState() != Qt.CheckState.Checked:
            QMessageBox.warning(
                self,
                "",
                '第一行预览未勾选「执行」。请先勾选或使用「勾选全部预览行」。',
            )
            return
        self._start_worker([(0, self._preview_row_cells(0))])

    def _on_run_all_preview(self) -> None:
        if not self._last_preview_rows:
            QMessageBox.information(self, "", "没有可执行的预览行，请先加载 Excel。")
            return
        pairs = self._selected_preview_pairs()
        self._start_worker(pairs)

    def _on_run_full_sheet(self) -> None:
        if not self._current_file:
            QMessageBox.information(self, "", "请先选择并加载 Excel。")
            return
        if not self._active_sheet_name():
            return
        self._start_worker(None, load_full_sheet=True)
