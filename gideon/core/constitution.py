"""Constitution — the rules that outrank everything.

Loads config/constitution.yaml (versioned in git). Defines:
- The Delivery Ledger: claims Nexora can actually back (no fake promises)
- Decision tiers: green (act alone) / yellow (propose) / red (never)

Safe default: anything unclassified is YELLOW — Gideon proposes, never assumes.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from gideon.config import CONFIG_DIR, get_settings

TIERS = ("green", "yellow", "red")

# Fallback mapping used if constitution.yaml is missing/unreadable.
# Unlisted actions default to yellow (propose) — safety first.
DEFAULT_ACTION_TIERS: dict[str, str] = {
    # green — decide alone, log in daily report
    "prioritize_leads": "green",
    "draft_message": "green",
    "schedule_followup": "green",
    "tune_playbook": "green",
    "choose_research_topic": "green",
    # yellow — propose, wait for owner
    "send_email": "yellow",  # becomes green later via autonomy ladder
    "change_pricing": "yellow",
    "offer_new_service": "yellow",
    "publish_content": "yellow",
    "spend_money": "yellow",
    "modify_own_code": "yellow",
    "change_channel": "yellow",
    # red — never
    "sign_contract": "red",
    "issue_refund": "red",
    "make_legal_claim": "red",
    "promise_beyond_ledger": "red",
    "post_as_nexora_unapproved": "red",
}


def _fallback_constitution() -> dict[str, Any]:
    return {
        "version": "fallback",
        "decision_tiers": {
            "green": [k for k, v in DEFAULT_ACTION_TIERS.items() if v == "green"],
            "yellow": [k for k, v in DEFAULT_ACTION_TIERS.items() if v == "yellow"],
            "red": [k for k, v in DEFAULT_ACTION_TIERS.items() if v == "red"],
        },
        "delivery_ledger": {"claims": []},
        "autonomy": {"level": "approve_first", "email_auto_send": False},
    }


@lru_cache(maxsize=1)
def load_constitution() -> dict[str, Any]:
    path = CONFIG_DIR / "constitution.yaml"
    if not path.exists():
        return _fallback_constitution()
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    # Merge safety: guarantee all three tiers exist
    tiers = data.setdefault("decision_tiers", {})
    for tier in TIERS:
        tiers.setdefault(tier, [])
    data.setdefault("delivery_ledger", {"claims": []})
    data.setdefault("autonomy", {"level": "approve_first", "email_auto_send": False})
    return data


def reset_constitution_cache() -> None:
    load_constitution.cache_clear()


def tier_for(action: str) -> str:
    """Classify an action. Unknown actions are YELLOW (propose)."""
    constitution = load_constitution()
    tiers = constitution.get("decision_tiers", {})
    for tier in TIERS:
        if action in tiers.get(tier, []):
            return tier
    return "yellow"


def ledger_claims() -> list[dict[str, Any]]:
    constitution = load_constitution()
    claims = constitution.get("delivery_ledger", {}).get("claims", [])
    return claims if isinstance(claims, list) else []


def autonomy_level() -> str:
    return str(load_constitution().get("autonomy", {}).get("level", "approve_first"))


def email_auto_send_enabled() -> bool:
    return bool(load_constitution().get("autonomy", {}).get("email_auto_send", False))


def assert_claim_allowed(claim: str) -> bool:
    """True only if the claim appears in the Delivery Ledger.

    Used by the promise guardrail: outbound copy must map to a ledger claim.
    Phase 1 populates the ledger; until then, non-empty claims are rejected.
    """
    claim_norm = " ".join(claim.lower().split())
    for entry in ledger_claims():
        text = str(entry.get("claim", "")) if isinstance(entry, dict) else str(entry)
        if claim_norm and claim_norm in " ".join(text.lower().split()):
            return True
    return False


def settings_autonomy() -> dict:
    return get_settings().get("autonomy", {}) or {}
