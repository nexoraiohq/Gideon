"""Phase 4 — research engine tests: watch list, sweep, opportunities, briefing."""

import pytest

from gideon.config import reset_settings_cache
from gideon.knowledge import ingest, store, targets
from gideon.memory import db
from gideon.research import briefing, opportunities, sweep, watchlist


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("GIDEON_DATA_DIR", str(tmp_path / "data"))
    reset_settings_cache()
    db.close_connection()
    yield
    db.close_connection()
    reset_settings_cache()


def _fake_page(url, **kwargs):
    if "down" in url:
        raise OSError("connection refused")
    return ("Mama Nzuri Salon in Kisii has no website and relies on walk-ins only. "
            "Salon Kings now offers new braiding services after expanding to a second branch.")


# ---------------------------------------------------------------------------
# Watch list
# ---------------------------------------------------------------------------
def test_add_watch_and_dedupe():
    wid = watchlist.add_watch("Booking Flow", "Nexora's core offer")
    assert watchlist.add_watch("booking flow") == wid  # re-activate, no duplicate
    items = watchlist.list_watch()
    assert len(items) == 1 and items[0]["term"] == "booking flow" and items[0]["active"] == 1


def test_remove_watch():
    wid = watchlist.add_watch("pricing")
    assert watchlist.remove_watch(wid) is True
    assert watchlist.list_watch() == []
    assert watchlist.remove_watch(999) is False


def test_empty_watch_rejected():
    with pytest.raises(ValueError):
        watchlist.add_watch("   ")


def test_watch_events_audited():
    wid = watchlist.add_watch("kisii market")
    watchlist.remove_watch(wid)
    kinds = [e["kind"] for e in db.recent_events(limit=50)]
    assert "watch_added" in kinds and "watch_removed" in kinds


# ---------------------------------------------------------------------------
# Sweep
# ---------------------------------------------------------------------------
def test_sweep_studies_active_targets(monkeypatch):
    monkeypatch.setattr(ingest, "fetch_page", _fake_page)
    targets.add_target("Salon A", "https://a.test")
    targets.add_target("Salon B", "https://b.test")

    report = sweep.sweep()
    assert report["targets_total"] == 2 and len(report["studied"]) == 2
    assert report["facts_learned"] > 0
    assert db.recent_events(kind="sweep_complete")


def test_sweep_survives_dead_target(monkeypatch):
    monkeypatch.setattr(ingest, "fetch_page", _fake_page)
    targets.add_target("Good", "https://good.test")
    targets.add_target("Down", "https://down.test")

    report = sweep.sweep()
    assert len(report["studied"]) == 1 and len(report["failed"]) == 1
    assert report["failed"][0]["name"] == "Down"
    assert "connection refused" in report["failed"][0]["error"]


def test_sweep_skips_paused_targets(monkeypatch):
    monkeypatch.setattr(ingest, "fetch_page", _fake_page)
    tid = targets.add_target("Paused", "https://p.test")
    targets.pause_target(tid)
    report = sweep.sweep()
    assert report["targets_total"] == 0


def test_sweep_specific_targets(monkeypatch):
    monkeypatch.setattr(ingest, "fetch_page", _fake_page)
    a = targets.add_target("A", "https://a.test")
    targets.add_target("B", "https://b.test")
    report = sweep.sweep(target_ids=[a])
    assert report["targets_total"] == 1 and report["studied"][0]["name"] == "A"


# ---------------------------------------------------------------------------
# Opportunity detectors
# ---------------------------------------------------------------------------
def _fact(text, **kw):
    return store.add_fact(text, **kw)


def test_weak_digital_detected():
    fid = _fact("Mama Nzuri Salon in Kisii has no website and relies on walk-ins.")
    hits = opportunities.detect_weak_digital(store.get_fact(fid))
    assert hits and hits[0].kind == "weak_digital"
    assert hits[0].evidence[0]["fact_id"] == fid


def test_weak_digital_ignores_normal_fact():
    fid = _fact("Nexora built a fast booking website for a Kisii salon.")
    assert opportunities.detect_weak_digital(store.get_fact(fid)) == []


def test_missing_booking_detected():
    fid = _fact("Glow Beauty Bar is a spa in Kisii offering hair and nail services.")
    hits = opportunities.detect_missing_booking(store.get_fact(fid))
    assert hits and hits[0].kind == "missing_booking"


def test_competitor_move_detected():
    fid = _fact("Salon Kings now offers new braiding services after expanding.")
    hits = opportunities.detect_competitor_move(store.get_fact(fid))
    assert hits and hits[0].kind == "competitor_move"


def test_local_signal_detected():
    fid = _fact("Kisii county hosts a beauty market event this December.")
    hits = opportunities.detect_local_signal(store.get_fact(fid))
    assert hits and hits[0].kind == "local_signal"


def test_detect_opportunities_dedupes_and_counts_evidence():
    _fact("Style Point Salon in Kisii has no website at all.")
    _fact("Another salon with no website in Kisii county.")
    hits = opportunities.detect_opportunities()
    weak = [h for h in hits if h["kind"] == "weak_digital"]
    assert len(weak) == 1                       # deduped by kind+title
    assert weak[0]["evidence_count"] == 2       # but both facts cited
    assert all("suggested_action" in h and "why" in h for h in hits)


# ---------------------------------------------------------------------------
# Briefing
# ---------------------------------------------------------------------------
def test_briefing_shape_and_text(monkeypatch):
    monkeypatch.setattr(ingest, "fetch_page", _fake_page)
    targets.add_target("Salon A", "https://a.test")
    watchlist.add_watch("booking")
    sweep.sweep()

    report = briefing.build_briefing()
    for key in ("date", "summary", "opportunities", "hunger", "text"):
        assert key in report
    assert report["summary"]["targets_studied"] == 1
    assert report["summary"]["facts_learned"] > 0
    assert "Good morning" in report["text"]
    assert "approval queue" in report["text"]


def test_briefing_empty_state_is_honest():
    report = briefing.build_briefing()
    assert "None detected yet" in report["text"]
    assert report["summary"]["sweeps"] == 0
    assert report["hunger"]["hungry"] is True   # nothing learned today


def test_briefing_mentions_failures(monkeypatch):
    monkeypatch.setattr(ingest, "fetch_page", _fake_page)
    targets.add_target("Down", "https://down.test")
    sweep.sweep()
    report = briefing.build_briefing()
    assert report["summary"]["failures"] == 1
    assert "could not study" in report["text"]
