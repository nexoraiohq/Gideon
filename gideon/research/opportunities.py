"""Opportunity detector — turning knowledge into actionable leads.

Heuristic rules over facts (local, explainable, zero deps). Each detector is a
plain function returning Opportunity hits with the evidence attached, so the
briefing can always answer "why?" — the owner never gets a black-box claim.

Detectors (v1 keyword heuristics; brain-scored later):
- weak_digital: business described with no site / outdated site / "no online"
- missing_booking: beauty/salon business without booking flow mentions
- competitor_move: competitor pricing/launch/expansion signals
- local_signal: Kisii/Kenya market activity (new salons, growth, events)

Every opportunity cites the fact(s) + source that triggered it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from gideon.knowledge import store

BUSINESS_WORDS = re.compile(
    r"\b(salon|barbershop|barber|spa|beauty|nail|hair|boutique|hotel|restaurant|"
    r"clinic|gym|school|agency|boda|pharmacy)\w*", re.IGNORECASE
)
WEAK_DIGITAL = re.compile(
    r"\b(no (online |digital )?presence|no website|not online|lacks? a website|"
    r"outdated website|old website|under construction|coming soon|facebook only|"
    r"instagram only|whatsapp only)\b", re.IGNORECASE
)
MISSING_BOOKING = re.compile(r"\b(booking|book online|appointment|reservation)s?\b",
                             re.IGNORECASE)
COMPETITOR_MOVE = re.compile(
    r"\b(new (service|location|branch|launch|pricing)s?|new \w+ services?|"
    r"price (cut|increase|change)s?|now offer\w*|just launched|expand\w*|"
    r"open(ed|ing))\b", re.IGNORECASE
)
LOCAL_SIGNAL = re.compile(
    r"\b(kisii|kisumu|nairobi|eldoret|nakuru|mombasa|kenya|nyamira|keroka|ogembo)\b",
    re.IGNORECASE
)


@dataclass
class Opportunity:
    kind: str
    title: str
    why: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    suggested_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "title": self.title,
            "why": self.why,
            "evidence": self.evidence,
            "suggested_action": self.suggested_action,
        }


Detector = Callable[[Any], list[Opportunity]]


def detect_weak_digital(fact: dict) -> list[Opportunity]:
    text = fact["content"]
    if BUSINESS_WORDS.search(text) and WEAK_DIGITAL.search(text):
        return [Opportunity(
            kind="weak_digital",
            title="Business with weak digital presence",
            why=f"fact describes a business with no/outdated online presence: "
                f"\"{text[:120]}\"",
            evidence=[{"fact_id": fact["id"], "source_url": fact["source_url"]}],
            suggested_action="qualify as a website lead — discovery call",
        )]
    return []


def detect_missing_booking(fact: dict) -> list[Opportunity]:
    text = fact["content"]
    if BUSINESS_WORDS.search(text) and not MISSING_BOOKING.search(text):
        # Salon-ish business described without any booking mention
        if re.search(r"\b(salon|barbershop|spa|beauty|hair|nail)\w*", text, re.IGNORECASE):
            return [Opportunity(
                kind="missing_booking",
                title="Beauty business without booking flow",
                why=f"fact describes a beauty business, no booking mentioned: "
                    f"\"{text[:120]}\"",
                evidence=[{"fact_id": fact["id"], "source_url": fact["source_url"]}],
                suggested_action="lead with the booking-flows case study",
            )]
    return []


def detect_competitor_move(fact: dict) -> list[Opportunity]:
    text = fact["content"]
    if COMPETITOR_MOVE.search(text):
        return [Opportunity(
            kind="competitor_move",
            title="Competitor moved — pricing/launch/expansion",
            why=f"signal detected: \"{text[:120]}\"",
            evidence=[{"fact_id": fact["id"], "source_url": fact["source_url"]}],
            suggested_action="review positioning; check if our offer needs a response",
        )]
    return []


def detect_local_signal(fact: dict) -> list[Opportunity]:
    text = fact["content"]
    if LOCAL_SIGNAL.search(text) and re.search(
        r"\b(opening|opened|new|growing|growth|event|festival|market)\w*", text,
        re.IGNORECASE
    ):
        return [Opportunity(
            kind="local_signal",
            title="Local market activity",
            why=f"regional signal: \"{text[:120]}\"",
            evidence=[{"fact_id": fact["id"], "source_url": fact["source_url"]}],
            suggested_action="consider localized outreach or content",
        )]
    return []


DEFAULT_DETECTORS: list[Detector] = [
    detect_weak_digital,
    detect_missing_booking,
    detect_competitor_move,
    detect_local_signal,
]


def detect_opportunities(
    *,
    approved_only: bool = False,
    limit: int = 500,
    detectors: list[Detector] | None = None,
) -> list[dict[str, Any]]:
    """Scan recent facts; return deduped opportunities with evidence."""
    facts = store.list_facts(approved=None if not approved_only else True, limit=limit)
    detectors = detectors or DEFAULT_DETECTORS

    hits: list[Opportunity] = []
    for fact in facts:
        for detect in detectors:
            hits.extend(detect(fact))

    # Dedupe by (kind, title): keep first (newest fact, list is DESC) with merged evidence
    merged: dict[tuple[str, str], Opportunity] = {}
    for hit in hits:
        key = (hit.kind, hit.title)
        if key in merged:
            merged[key].evidence.extend(hit.evidence)
        else:
            merged[key] = hit

    out = [op.to_dict() for op in merged.values()]
    for op in out:
        op["evidence_count"] = len(op["evidence"])
    return out
