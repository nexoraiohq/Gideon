"""Database tests â€” migrations, append-only events, screens, isolated data dir."""

import pytest

from gideon.config import get_settings, reset_settings_cache
from gideon.memory import db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point Gideon at a throwaway data dir for every test."""
    monkeypatch.setenv("GIDEON_DATA_DIR", str(tmp_path / "data"))
    reset_settings_cache()
    db.close_connection()
    yield
    db.close_connection()
    reset_settings_cache()


def test_init_db_applies_migrations():
    applied = db.init_db()
    assert applied == [1, 2, 3, 4]
    # second run is a no-op (idempotent â€” nothing breaks on restart)
    assert db.init_db() == []


def test_existing_db_gets_new_migrations():
    """Regression: an old DB (only migration 1) must gain migration 2 on next connect."""
    import sqlite3
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        old_path = Path(tmp) / "old.db"
        # Forge a v1-era database: schema_migrations + migration-1 tables only
        conn = sqlite3.connect(old_path)
        conn.executescript(db.MIGRATIONS[0][1])
        conn.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES(1, '2026-01-01')"
        )
        conn.commit()
        conn.close()

        conn = db._connect(old_path)
        try:
            db._ensure_schema(conn)
            tables = {
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            versions = [
                r["version"]
                for r in conn.execute("SELECT version FROM schema_migrations")
            ]
        finally:
            conn.close()
        assert "targets" in tables   # migration 2 landed
        assert "watchlist" in tables  # migration 3 landed
        assert sorted(versions) == [1, 2, 3, 4]


def test_events_append_and_read():
    db.init_db()
    db.record_event("test", "first event", {"x": 1})
    db.record_event("test", "second event")
    events = db.recent_events(kind="test")
    assert len(events) == 2
    assert events[0]["summary"] == "second event"  # newest first
    assert events[1]["payload"] == {"x": 1}


def test_screen_saved_to_db_and_file():
    db.init_db()
    screen_id = db.save_screen("evidence", "Why spas?", {"chart": "reply_rates"})
    assert screen_id >= 1
    assert any(s["title"] == "Why spas?" for s in db.list_screens())
    files = list(get_settings().screens_dir.glob("screen_*.json"))
    assert len(files) == 1


def test_healthcheck_ok():
    db.init_db()
    health = db.healthcheck()
    assert health["ok"] is True
    assert "events" in health["tables"]
    assert "screens" in health["tables"]


def test_data_dir_outside_project_when_env_set(tmp_path):
    settings = get_settings()
    assert str(tmp_path) in str(settings.data_dir)

