"""Phase 5 — prospecting tests: extraction, scoring, finder, pipeline."""

import json

import pytest

from gideon.config import reset_settings_cache
from gideon.knowledge import store
from gideon.memory import db
from gideon.sales import leads, pipeline, scoring


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("GIDEON_DATA_DIR", str(tmp_path / "data"))
    reset_settings_cache()
    db.close_connection()
    yield
    db.close_connection()
    reset_settings_cache()


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
def test_extract_named_business_before_industry_word():
    text = "Mama Nzuri Salon opened last year. Style Point Barbershop is nearby."
    found = {b["name"] for b in leads.extract_businesses(text)}
    assert "Mama Nzuri Salon" in found
    assert "Style Point Barbershop" in found


def test_extract_business_is_a_style():
    text = "Glow Beauty Bar is a salon in Kisii offering hair services."
    found = leads.extract_businesses(text)
    glow = next(b for b in found if b["name"] == "Glow Beauty Bar")
    assert glow["kind"] in ("salon", "beauty bar")
    assert glow["location"] == "Kisii"


def test_extract_ignores_generic_sentences():
    text = "It is a salon that anyone can visit. This is a spa for everyone."
    found = leads.extract_businesses(text)
    names = {b["name"].lower() for b in found}
    assert not any(n.startswith(("it is", "this is")) for n in names)


def test_extract_attaches_kenya_location():
    text = "Braided Dreams Salon is a new shop in Nyamira."
    found = leads.extract_businesses(text)
    assert found and found[0]["location"] == "Nyamira"


def test_extract_drops_marketing_copy_and_self():
    text = ("Best Salon Websites Kenya. Barbershop Website Design examples. "
            "Nexora Studio builds them.")
    found = leads.extract_businesses(text)
    names = {b["name"].lower() for b in found}
    assert not any("website" in n or "web design" in n for n in names)
    assert "nexora studio" not in names                  # never prospect ourselves


def test_extract_never_prospects_existing_clients():
    text = "States Barbershop lacked a dedicated website. How we built a stronger presence."
    found = leads.extract_businesses(text)
    assert not any(b["name"].lower() == "states barbershop" for b in found)


def test_extract_drops_connector_and_industry_fragments():
    text = ("Espresso Salon Spa and Barbershop is a salon in Kisii. "
            "Nisa Boutique and Hair Saloon is a hair salon in Kisii town.")
    names = {b["name"].lower() for b in leads.extract_businesses(text)}
    assert "spa and barbershop" not in names
    assert "and hair saloon" not in names
    assert "hair salon" not in names
    # the real names in the same sentences still come through
    assert "espresso salon spa" in names


# ---------------------------------------------------------------------------
# Scoring — every point has a reason
# ---------------------------------------------------------------------------
def test_hot_lead_scores_high_with_reasons():
    lead = {"name": "Glow Salon", "kind": "salon", "location": "Kisii",
            "notes": "no website, whatsapp only; opening new branch"}
    result = scoring.score_lead(lead)
    assert result["score"] >= 70
    assert scoring.grade(result["score"]) == "A"
    joined = " ".join(result["reasons"])
    assert "salon" in joined.lower()
    assert "Kisii" in joined
    assert "no website" in joined or "whatsapp only" in joined


def test_cold_lead_scores_low_and_says_why():
    result = scoring.score_lead({"name": "Random Thing", "kind": "shop",
                                 "location": "Somewhere", "notes": ""})
    assert result["score"] < 30
    assert "low priority" in " ".join(result["reasons"])


def test_score_reasons_add_up_to_score():
    lead = {"name": "Kisii Nails", "kind": "nail studio", "location": "Kisii",
            "url": "https://x.test", "notes": "no online presence, rebranding"}
    result = scoring.score_lead(lead)
    points = sum(int(r.split("+")[1].split(" ")[0]) for r in result["reasons"]
                 if r.startswith("+"))
    assert points == result["score"]


def test_grades_boundaries():
    assert scoring.grade(70) == "A"
    assert scoring.grade(69) == "B"
    assert scoring.grade(50) == "B"
    assert scoring.grade(30) == "C"
    assert scoring.grade(29) == "D"


# ---------------------------------------------------------------------------
# Leads repo + finder
# ---------------------------------------------------------------------------
def test_add_lead_scores_and_audits():
    lid = leads.add_lead("Glow Salon", "salon", "Kisii",
                         notes="no website, whatsapp only")
    lead = leads.get_lead(lid)
    assert lead["score"] >= 70 and lead["stage"] == "new"
    assert isinstance(lead["reasons"], list) and lead["reasons"]
    assert db.recent_events(kind="lead_found")


def test_add_lead_needs_name():
    with pytest.raises(ValueError):
        leads.add_lead("   ")


def test_find_leads_mines_knowledge_and_dedupes():
    store.add_fact("Glow Beauty Bar is a salon in Kisii with no website.",
                   source_url="https://a.test")
    store.add_fact("Glow Beauty Bar — WhatsApp only for bookings.",
                   source_url="https://a.test")

    report = leads.find_leads(min_score=30)
    names = [a["name"] for a in report["added"]]
    assert names.count("Glow Beauty Bar") == 1          # deduped
    assert report["added"][0]["score"] >= 70

    again = leads.find_leads(min_score=30)
    assert again["added"] == []                          # second run: nothing new
    assert again["skipped_existing"] >= 1


def test_find_leads_respects_min_score():
    store.add_fact("Random shop in town, things sold.")
    report = leads.find_leads(min_score=30)
    assert report["added"] == [] or all(a["score"] >= 30 for a in report["added"])


def test_list_leads_filters_and_sorts():
    leads.add_lead("Cold One", "shop", "Far Away")
    leads.add_lead("Hot One", "salon", "Kisii", notes="no website, whatsapp only")
    items = leads.list_leads()
    assert items[0]["name"] == "Hot One"                # sorted by score DESC
    assert leads.list_leads(min_score=50)[0]["name"] == "Hot One"
    assert all(i["score"] >= 50 for i in leads.list_leads(min_score=50))


# ---------------------------------------------------------------------------
# Pipeline — the tiny CRM
# ---------------------------------------------------------------------------
def _hot_lead() -> int:
    return leads.add_lead("Glow Salon", "salon", "Kisii",
                          notes="no website, whatsapp only")


def test_happy_path_new_to_won():
    lid = _hot_lead()
    for stage in ("contacted", "replied", "proposal", "won"):
        result = pipeline.move_stage(lid, stage)
        assert result["stage"] == stage and result["changed"] is True
    assert leads.get_lead(lid)["stage"] == "won"


def test_pipeline_rejects_teleport():
    lid = _hot_lead()
    with pytest.raises(ValueError, match="cannot move"):
        pipeline.move_stage(lid, "won")                  # new → won = fantasy


def test_pipeline_rejects_unknown_stage():
    lid = _hot_lead()
    with pytest.raises(ValueError, match="unknown stage"):
        pipeline.move_stage(lid, "skyrocketed")


def test_pipeline_lost_from_new_is_allowed():
    lid = _hot_lead()
    assert pipeline.move_stage(lid, "lost")["stage"] == "lost"
    with pytest.raises(ValueError):                      # terminal states hold
        pipeline.move_stage(lid, "contacted")


def test_pipeline_same_stage_is_noop():
    lid = _hot_lead()
    result = pipeline.move_stage(lid, "new")
    assert result["changed"] is False


def test_pipeline_missing_lead():
    with pytest.raises(ValueError, match="not found"):
        pipeline.move_stage(999, "contacted")


def test_pipeline_moves_are_audited_with_note():
    lid = _hot_lead()
    pipeline.move_stage(lid, "contacted", note="WhatsApp sent")
    events = db.recent_events(kind="lead_stage_changed")
    assert events and events[0]["payload"]["note"] == "WhatsApp sent"
    assert "contacted" in leads.get_lead(lid)["notes"]


def test_pipeline_report_counts():
    hot = _hot_lead()
    cold = leads.add_lead("Cold One", "shop", "Far Away")
    pipeline.move_stage(hot, "contacted")
    pipeline.move_stage(hot, "replied")
    pipeline.move_stage(cold, "lost")
    report = pipeline.pipeline_report()
    assert report["total"] == 2
    assert report["counts"]["replied"] == 1 and report["counts"]["lost"] == 1
    assert report["win_rate"] == 0.0


def test_pipeline_report_empty():
    report = pipeline.pipeline_report()
    assert report["total"] == 0 and report["win_rate"] == 0.0
    assert json.loads(report["snapshot"])["won"] == 0
