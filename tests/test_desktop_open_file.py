from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from rpa_assistant.app.automation.desktop import run_step


def test_open_file_missing_path() -> None:
    r = run_step("open_file", {})
    assert not r.ok
    assert "路径" in (r.message or "")


def test_open_file_not_found(tmp_path: Path) -> None:
    p = tmp_path / "nope.txt"
    r = run_step("open_file", {"path": str(p)})
    assert not r.ok
    assert "不存在" in (r.message or "")


@patch("rpa_assistant.app.automation.desktop.subprocess.run")
def test_open_file_darwin(mock_run, tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_text("x", encoding="utf-8")
    with patch("sys.platform", "darwin"):
        r = run_step("open_file", {"path": str(f)})
    assert r.ok
    mock_run.assert_called_once_with(["open", str(f)], check=True)


@patch("rpa_assistant.app.automation.desktop.os.startfile", create=True)
def test_open_file_windows(mock_sf, tmp_path: Path) -> None:
    f = tmp_path / "b.txt"
    f.write_text("y", encoding="utf-8")
    with patch("sys.platform", "win32"):
        r = run_step("open_file", {"path": str(f)})
    assert r.ok
    mock_sf.assert_called_once_with(str(f))
