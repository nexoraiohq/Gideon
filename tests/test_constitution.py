"""Constitution tests — the safety rules must hold, always."""

from gideon.core.constitution import (
    DEFAULT_ACTION_TIERS,
    TIERS,
    assert_claim_allowed,
    autonomy_level,
    email_auto_send_enabled,
    load_constitution,
    ledger_claims,
    tier_for,
)


def test_three_tiers_exist():
    data = load_constitution()
    for tier in TIERS:
        assert tier in data["decision_tiers"]


def test_known_actions_classified():
    assert tier_for("prioritize_leads") == "green"
    assert tier_for("change_pricing") == "yellow"
    assert tier_for("sign_contract") == "red"


def test_unknown_action_defaults_to_yellow():
    """Safe default: anything unclassified is proposed, never assumed."""
    assert tier_for("do_something_unheard_of") == "yellow"


def test_ledger_has_verified_claims():
    claims = ledger_claims()
    assert len(claims) >= 5
    assert all("claim" in c for c in claims)


def test_promise_guardrail():
    # Verified ledger phrase passes; invented superlative fails
    assert assert_claim_allowed("mobile-first websites for salons") is True
    assert assert_claim_allowed("we are the #1 web agency in Africa") is False


def test_autonomy_locked_to_approve_first():
    assert autonomy_level() == "approve_first"
    assert email_auto_send_enabled() is False


def test_default_tiers_cover_all_values():
    assert set(DEFAULT_ACTION_TIERS.values()) == set(TIERS)
