from __future__ import annotations

from pathlib import Path

from rpa_assistant.app.models import (
    ConfigPayload,
    ExecutionRecord,
    ExecutionStatus,
    FlowStatus,
    StepRunRecord,
    StepRunStatus,
)
from rpa_assistant.app.storage.config_repo import ConfigRepository
from rpa_assistant.app.storage.database import CURRENT_SCHEMA_VERSION, init_database
from rpa_assistant.app.storage.execution_repo import ExecutionRepository
from rpa_assistant.app.storage.flow_repo import FlowRepository


def _db(path: Path) -> Path:
    init_database(path)
    return path


def test_schema_version_is_2(tmp_path: Path) -> None:
    db = tmp_path / "a.sqlite3"
    _db(db)
    assert CURRENT_SCHEMA_VERSION == 2


def test_config_round_trip(tmp_path: Path) -> None:
    db = tmp_path / "c.sqlite3"
    _db(db)
    cfg = ConfigRepository(db)
    payload = ConfigPayload(
        flow_id="flow-1",
        target_window_title="记事本",
        extra={"custom": 1},
    )
    cid = cfg.create("办公配置", payload, is_default=True)
    got = cfg.get(cid)
    assert got is not None
    assert got.payload.flow_id == "flow-1"
    assert got.payload.target_window_title == "记事本"
    assert cfg.get_default() is not None and cfg.get_default().id == cid


def test_flow_round_trip(tmp_path: Path) -> None:
    db = tmp_path / "f.sqlite3"
    _db(db)
    flows = FlowRepository(db)
    fid = flows.create(
        "合同流程",
        {"steps": [{"type": "wait", "ms": 100}]},
        status=FlowStatus.ACTIVE,
    )
    r = flows.get(fid)
    assert r is not None
    assert r.definition["steps"][0]["type"] == "wait"
    r.definition["version"] = 2
    flows.save(r)
    assert flows.get(fid).definition.get("version") == 2


def test_execution_and_step_runs(tmp_path: Path) -> None:
    db = tmp_path / "e.sqlite3"
    _db(db)
    flows = FlowRepository(db)
    fid = flows.create("f", {"steps": []})

    ex_repo = ExecutionRepository(db)
    ex = ExecutionRecord(
        id="",
        status=ExecutionStatus.RUNNING,
        batch_id="batch-1",
        flow_id=fid,
        config_id=None,
        variables={"用户编号": "U1"},
        source_sheet="Sheet1",
        source_row_index=3,
    )
    eid = ex_repo.create_execution(ex)
    sr = StepRunRecord(
        id="",
        execution_id=eid,
        status=StepRunStatus.SUCCESS,
        order_index=0,
        step_type="wait",
        strategy_used="native",
        output_data={"ok": True},
    )
    ex_repo.add_step_run(sr)

    loaded = ex_repo.get(eid)
    assert loaded is not None
    assert loaded.variables == {"用户编号": "U1"}
    assert loaded.source_row_index == 3
    steps = ex_repo.list_step_runs(eid)
    assert len(steps) == 1
    assert steps[0].strategy_used == "native"


def test_list_by_batch(tmp_path: Path) -> None:
    db = tmp_path / "b.sqlite3"
    _db(db)
    ex_repo = ExecutionRepository(db)
    a = ex_repo.create_execution(
        ExecutionRecord(
            id="",
            status=ExecutionStatus.PENDING,
            batch_id="B0",
        )
    )
    b = ex_repo.create_execution(
        ExecutionRecord(
            id="",
            status=ExecutionStatus.PENDING,
            batch_id="B0",
        )
    )
    rows = ex_repo.list_by_batch("B0")
    assert {r.id for r in rows} == {a, b}
