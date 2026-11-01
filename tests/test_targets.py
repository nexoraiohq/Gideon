"""Phase 3 — learning loop tests: targets, research, approval queue."""

from datetime import datetime, timezone

import pytest

from gideon.config import reset_settings_cache
from gideon.knowledge import ingest, store, targets
from gideon.memory import db


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("GIDEON_DATA_DIR", str(tmp_path / "data"))
    reset_settings_cache()
    db.close_connection()
    yield
    db.close_connection()
    reset_settings_cache()


# ---------------------------------------------------------------------------
# Targets CRUD
# ---------------------------------------------------------------------------
def test_add_target_and_list():
    tid = targets.add_target("Salon Kings", "https://salkings.test", "competitor")
    items = targets.list_targets()
    assert len(items) == 1
    assert items[0]["id"] == tid
    assert items[0]["name"] == "Salon Kings"
    assert items[0]["active"] == 1
    assert items[0]["last_researched"] is None


def test_add_target_validates():
    with pytest.raises(ValueError, match="name and a url"):
        targets.add_target("", "https://x.test")
    with pytest.raises(ValueError, match="http"):
        targets.add_target("No URL Co", "ftp://bad")
    with pytest.raises(ValueError, match="kind"):
        targets.add_target("Bad Kind", "https://x.test", "aliens")


def test_target_added_is_audited():
    tid = targets.add_target("Market A", "https://a.test", "market")
    events = db.recent_events(kind="target_added")
    assert events and events[0]["payload"]["target_id"] == tid


def test_pause_target():
    tid = targets.add_target("Prospect B", "https://b.test", "prospect")
    assert targets.pause_target(tid) is True
    assert targets.list_targets() == []            # active-only default
    assert len(targets.list_targets(active_only=False)) == 1
    assert targets.pause_target(999) is False


# ---------------------------------------------------------------------------
# Research loop (fetch mocked — tests never touch the network)
# ---------------------------------------------------------------------------
def _fake_page(url: str, *, timeout: float = 20.0) -> str:
    return ("Salon Kings offers hair styling and braiding in Kisii. "
            "They accept walk-ins and have a website with a gallery.")


def test_research_target_lands_facts_unapproved(monkeypatch):
    monkeypatch.setattr(ingest, "fetch_page", _fake_page)
    tid = targets.add_target("Salon Kings", "https://salkings.test")

    result = targets.research_target(tid)
    assert result["ok"] is True and len(result["added"]) == 2

    facts = store.list_facts()
    assert len(facts) == 2
    assert all(f["approved"] == 0 for f in facts)              # the gate
    assert all(f["source_url"] == "https://salkings.test" for f in facts)

    t = targets.get_target(tid)
    assert t["last_researched"] is not None


def test_research_records_events(monkeypatch):
    monkeypatch.setattr(ingest, "fetch_page", _fake_page)
    tid = targets.add_target("Salon Kings", "https://salkings.test")
    targets.research_target(tid)
    events = db.recent_events(kind="research_complete")
    assert events and "awaiting approval" in events[0]["summary"]


def test_research_failure_is_reported_not_swallowed(monkeypatch):
    def boom(url, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(ingest, "fetch_page", boom)
    tid = targets.add_target("Down Site", "https://down.test")

    result = targets.research_target(tid)
    assert result["ok"] is False and "connection refused" in result["error"]
    assert db.recent_events(kind="research_failed")
    assert targets.get_target(tid)["last_researched"] is None


def test_research_rejects_missing_or_paused(monkeypatch):
    monkeypatch.setattr(ingest, "fetch_page", _fake_page)
    with pytest.raises(ValueError, match="not found"):
        targets.research_target(999)
    tid = targets.add_target("Paused Co", "https://p.test")
    targets.pause_target(tid)
    with pytest.raises(ValueError, match="paused"):
        targets.research_target(tid)


def test_research_dedupes_across_runs(monkeypatch):
    monkeypatch.setattr(ingest, "fetch_page", _fake_page)
    tid = targets.add_target("Salon Kings", "https://salkings.test")
    first = targets.research_target(tid)
    second = targets.research_target(tid)
    assert len(first["added"]) == 2 and second["added"] == [] and second["skipped"] == 2


# ---------------------------------------------------------------------------
# Approval queue + hunger report
# ---------------------------------------------------------------------------
def test_approval_queue_lists_only_unapproved():
    store.add_fact("Approved fact stays out of queue.", approved=True)
    store.add_fact("Pending fact waits for owner.")
    queue = targets.approval_queue()
    assert len(queue) == 1 and "Pending" in queue[0]["content"]


def test_hunger_report_shape():
    report = targets.hunger_report()
    for key in ("hunger", "active_targets", "pending_approvals", "approved_facts"):
        assert key in report
    assert report["active_targets"] == 0


def test_full_loop_target_to_memory(monkeypatch):
    """The Phase 3 acceptance test: URL → facts → approve → memory."""
    monkeypatch.setattr(ingest, "fetch_page", _fake_page)
    tid = targets.add_target("Salon Kings", "https://salkings.test", "competitor")
    result = targets.research_target(tid)

    # owner reviews the queue and approves
    for fact in targets.approval_queue():
        store.approve_fact(fact["id"])

    assert store.count_facts(approved=True) == len(result["added"])
    hits = store.search_facts("hair styling braiding")
    assert hits and hits[0]["source_url"] == "https://salkings.test"
