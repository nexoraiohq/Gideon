"""Hunger tests — Gideon always wants to learn; floors drive its reports."""

import pytest

from gideon.brain import hunger
from gideon.config import reset_settings_cache
from gideon.memory import db


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("GIDEON_DATA_DIR", str(tmp_path / "data"))
    reset_settings_cache()
    db.close_connection()
    yield
    db.close_connection()
    reset_settings_cache()


def test_empty_day_is_hungry():
    status = hunger.hunger_status(today="1999-01-01")
    assert status["hungry"] is True
    assert "Hungry" in status["message"]


def test_intake_recorded_and_audited():
    hunger.record_intake("nexora.io/blog", 1200, kind="web")
    events = db.recent_events(kind="knowledge_intake")
    assert len(events) == 1
    assert events[0]["payload"]["chars"] == 1200
    assert "learned 1,200 chars" in events[0]["summary"]


def test_feeds_after_meeting_floors():
    # floors: 5 items AND 8000 chars (settings.yaml → hunger.*)
    for _ in range(5):
        hunger.record_intake("source.txt", 2000)
    status = hunger.hunger_status()
    assert status["items"] == 5
    assert status["chars"] == 10000
    assert status["hungry"] is False
    assert "intake satisfied" in status["message"]


def test_partial_day_still_hungry():
    hunger.record_intake("only-one.txt", 2000)
    status = hunger.hunger_status()
    assert status["hungry"] is True  # 1/5 items, 2000/8000 chars


def test_retrain_threshold():
    assert hunger.should_retrain(19_999) is False
    assert hunger.should_retrain(20_000) is True
    assert "feeding threshold" in hunger.retrain_message(30_000)


def test_status_is_a_plain_reportable_dict():
    status = hunger.hunger_status()
    for key in ("day", "items", "chars", "hungry", "message"):
        assert key in status
