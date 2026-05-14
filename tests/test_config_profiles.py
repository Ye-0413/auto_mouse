from __future__ import annotations

from pathlib import Path

from rpa_assistant.app.models.config import ConfigPayload
from rpa_assistant.app.storage.config_repo import ConfigRepository
from rpa_assistant.app.storage.database import init_database


def test_config_profiles_default_switch(tmp_path: Path) -> None:
    db = tmp_path / "c.sqlite3"
    init_database(db)
    repo = ConfigRepository(db)
    a = repo.ensure_default()
    assert a.is_default

    b_id = repo.create("备用", ConfigPayload(), is_default=False)
    b2 = repo.get(b_id)
    assert b2 and not b2.is_default

    b2.is_default = True
    repo.save(b2)
    af = repo.get(a.id)
    bf = repo.get(b_id)
    assert af and not af.is_default
    assert bf and bf.is_default
