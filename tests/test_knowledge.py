"""Phase 2 — knowledge store + ingestion tests."""

import pytest

from gideon.config import reset_settings_cache
from gideon.knowledge import ingest, store
from gideon.memory import db


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("GIDEON_DATA_DIR", str(tmp_path / "data"))
    reset_settings_cache()
    db.close_connection()
    yield
    db.close_connection()
    reset_settings_cache()


def test_add_fact_is_unapproved_by_default():
    fid = store.add_fact("Nexora builds websites in Kisii.", "about", "https://x.test")
    fact = store.get_fact(fid)
    assert fact["approved"] == 0
    assert fact["source_url"] == "https://x.test"
    assert fact["learned_at"]


def test_empty_fact_rejected():
    with pytest.raises(ValueError):
        store.add_fact("   ")


def test_approve_fact_and_audit_event():
    fid = store.add_fact("Booking flows are included.", "services")
    assert store.approve_fact(fid) is True
    assert store.get_fact(fid)["approved"] == 1
    events = db.recent_events(kind="fact_approved")
    assert events and events[0]["payload"]["fact_id"] == fid
    # approving twice is a no-op
    assert store.approve_fact(fid) is False


def test_search_ranks_by_overlap_and_respects_approval():
    store.add_fact("Nexora designs booking flows for salons.", "services", approved=True)
    store.add_fact("The weather in Kisii is warm.", "general", approved=True)
    store.add_fact("Nexora builds WhatsApp integrations.", "services", approved=False)

    hits = store.search_facts("booking flow for salons")
    assert hits and "booking" in hits[0]["content"].lower()
    # unapproved fact must not appear by default
    assert all("whatsapp" not in h["content"].lower() for h in hits)
    # ...but is findable when explicitly requested
    raw = store.search_facts("whatsapp integration", approved_only=False)
    assert any("whatsapp" in h["content"].lower() for h in raw)


def test_search_empty_query_returns_nothing():
    assert store.search_facts("   ") == []


def test_count_facts():
    store.add_fact("Fact one about Nexora services.", approved=True)
    store.add_fact("Fact two about pricing.", approved=False)
    assert store.count_facts() == 2
    assert store.count_facts(approved=True) == 1
    assert store.count_facts(approved=False) == 1


def test_html_to_text_strips_noise():
    html = """
    <html><head><script>var x=1;</script><style>.a{color:red}</style></head>
    <body><nav>Home Services</nav><h1>Nexora Studio</h1>
    <p>We build websites &amp; systems.</p></body></html>
    """
    text = ingest.html_to_text(html)
    assert "var x" not in text and "color" not in text
    assert "Nexora Studio" in text and "websites & systems" in text
    assert "<" not in text


def test_split_facts_makes_one_idea_each():
    text = ("Nexora builds fast websites. Booking flows are included in every build. "
            "short")  # 'short' < MIN_FACT_CHARS → dropped
    facts = ingest.split_facts(text)
    assert len(facts) == 2
    assert all(len(f) >= 25 for f in facts)


def test_split_facts_breaks_long_sentences():
    text = "Nexora provides " + "very detailed and extended explanation words " * 30 + "end."
    facts = ingest.split_facts(text)
    assert len(facts) > 1
    assert all(len(f) <= ingest.MAX_FACT_CHARS for f in facts)


def test_guess_category():
    assert ingest.guess_category("Our pricing starts at a deposit") == "pricing"
    assert ingest.guess_category("We design landing pages") == "services"
    assert ingest.guess_category("Based in Kisii, Kenya") == "about"
    assert ingest.guess_category("Rain today") == "general"


def test_ingest_text_creates_facts_and_dedupes():
    text = ("Nexora is a website design studio in Kisii, Kenya. "
            "We build booking flows for salons and barbershops. ") * 1
    first = ingest.ingest_text(text, source="https://nexora.test")
    assert len(first["added"]) == 2
    assert first["chars"] == len(text)

    second = ingest.ingest_text(text, source="https://nexora.test")
    assert second["added"] == []
    assert second["skipped"] == 2

    facts = store.list_facts()
    assert all(f["source_url"] == "https://nexora.test" for f in facts)


def test_ingest_records_hunger_intake():
    from gideon.brain import hunger

    ingest.ingest_text("Nexora builds professional websites for growing businesses.",
                       source="page.test")
    status = hunger.hunger_status()
    assert status["items"] == 1 and status["chars"] > 0


def test_discover_same_site_urls():
    html = '''
    <a href="/services">Services</a>
    <a href="https://other.test/spam">spam</a>
    <a href="/work.png">image</a>
    <a href="https://nexoraio.vercel.app/about">About</a>
    '''
    urls = ingest.discover_same_site_urls("https://nexoraio.vercel.app/", html)
    assert "https://nexoraio.vercel.app/services" in urls
    assert "https://nexoraio.vercel.app/about" in urls
    assert all("other.test" not in u and ".png" not in u for u in urls)
