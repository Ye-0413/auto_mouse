from __future__ import annotations

from pathlib import Path

import openpyxl

from rpa_assistant.app.excel.mapper import row_to_variables
from rpa_assistant.app.excel.reader import load_sheet_snapshot, open_workbook_meta
from rpa_assistant.app.excel.validator import validate_rows


def _write_sample(path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Sheet1"
    ws.append(["用户编号", "合同类型", "金额"])
    ws.append(["U1", "A", 10])
    ws.append(["U2", "B", 20])
    ws.append(["U1", "C", 30])  # duplicate key U1 on purpose
    wb.save(path)


def test_open_meta_and_load_snapshot(tmp_path: Path) -> None:
    xlsx = tmp_path / "t.xlsx"
    _write_sample(xlsx)
    names = open_workbook_meta(xlsx)
    assert "Sheet1" in names
    snap = load_sheet_snapshot(xlsx, "Sheet1", header_row_1based=1)
    assert snap.headers == ["用户编号", "合同类型", "金额"]
    assert len(snap.preview_rows) == 3
    assert snap.data_row_count == 3


def test_validate_primary_duplicate(tmp_path: Path) -> None:
    xlsx = tmp_path / "t.xlsx"
    _write_sample(xlsx)
    snap = load_sheet_snapshot(xlsx, "Sheet1", header_row_1based=1)
    issues = validate_rows(
        snap.headers,
        snap.preview_rows,
        primary_key_header="用户编号",
        mapped_columns=["用户编号", "合同类型"],
    )
    assert any("主键重复" in m for iss in issues for m in iss.messages)


def test_row_to_variables() -> None:
    h = ["用户编号", "合同类型"]
    r = ["U9", "低压居民供用电合同"]
    vmap = {"用户编号": "uid", "合同类型": "ctype"}
    out = row_to_variables(h, r, vmap)
    assert out == {"uid": "U9", "ctype": "低压居民供用电合同"}
