"""#54: db must follow settings.DB_PATH at call time, not a path cached on first use."""

import asyncio

from app import db


def test_db_follows_settings_db_path_changes(tmp_path, monkeypatch):
    first, second = tmp_path / "first.db", tmp_path / "second.db"
    monkeypatch.setattr("app.config.settings.DB_PATH", str(first))
    asyncio.run(db.init_db())

    monkeypatch.setattr("app.config.settings.DB_PATH", str(second))
    asyncio.run(db.init_db())

    assert second.exists()
