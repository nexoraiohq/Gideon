"""Phase 2 — cited answers + promise guardrail tests."""

import pytest

from gideon.config import reset_settings_cache
from gideon.core import guardrail
from gideon.knowledge import answer as knowledge_answer
from gideon.knowledge import store
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
# Cited answers
# ---------------------------------------------------------------------------
def test_answer_without_knowledge_admits_it():
    result = knowledge_answer.answer("what does nexora do?")
    assert result["needs_research"] is True
    assert result["citations"] == [] and result["confidence"] == 0.0
    assert "don't have" in result["answer"]


def test_answer_cites_approved_facts():
    store.add_fact("Nexora builds fast, mobile-first websites for salons in Kisii.",
                   "about", "https://nexoraio.vercel.app/", approved=True)
    result = knowledge_answer.answer("what websites does nexora build for salons?")
    assert result["needs_research"] is False
    assert result["confidence"] > 0.25
    assert result["citations"][0]["source_url"] == "https://nexoraio.vercel.app/"
    assert result["answer"].startswith(("Based on", "What I have so far"))


def test_answer_never_cites_unapproved_facts():
    store.add_fact("Nexora guarantees first page rankings on Google.", approved=False)
    result = knowledge_answer.answer("does nexora guarantee google rankings?")
    assert result["needs_research"] is True
    assert result["citations"] == []


def test_answer_flags_unbacked_promise_in_body():
    store.add_fact("We guarantee you will double your revenue with our websites.",
                   approved=True)
    result = knowledge_answer.answer("do you guarantee revenue results?")
    assert result["promise_flagged"] is True


def test_empty_question_rejected():
    with pytest.raises(ValueError):
        knowledge_answer.answer("   ")


# ---------------------------------------------------------------------------
# Promise guardrail
# ---------------------------------------------------------------------------
def test_clean_copy_is_green():
    check = guardrail.check_draft(
        "Hi Sarah, we build fast websites for salons in Kisii. "
        "We can also set up WhatsApp enquiries on your site."
    )
    assert check.verdict == "green" and check.ok_to_send
    assert check.red_flags == [] and check.yellow_flags == []


def test_guarantee_language_is_red():
    check = guardrail.check_draft("We guarantee you will be on the first page.")
    assert check.verdict == "red" and not check.ok_to_send
    assert check.red_flags[0]["rule"] == "guarantee language"


def test_refund_promise_is_red():
    check = guardrail.check_draft("If you're unhappy, we offer a full refund.")
    assert check.verdict == "red"


def test_unbacked_outcome_promise_is_yellow():
    check = guardrail.check_draft("Our websites will double your sales this quarter.")
    assert check.verdict == "yellow" and not check.ok_to_send
    assert check.yellow_flags[0]["rule"] == "outcome promise"
    assert "review" in check.to_dict()["message"].lower()


def test_ledger_backed_timeline_is_not_yellow():
    # 50% deposit before launch IS in the ledger → documented promise stays clean
    check = guardrail.check_draft("Payment is 50% deposit with 50% due before launch.")
    assert check.verdict == "green"


def test_red_beats_yellow():
    check = guardrail.check_draft(
        "Our websites double your sales, and we guarantee first page rankings."
    )
    assert check.verdict == "red"


def test_empty_draft_is_green():
    assert guardrail.check_draft("").verdict == "green"


def test_check_result_serializes_for_api():
    data = guardrail.check_draft("We guarantee results.").to_dict()
    for key in ("verdict", "ok_to_send", "red_flags", "yellow_flags", "message"):
        assert key in data
