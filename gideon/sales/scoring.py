"""Lead scoring — does this prospect fit what Nexora actually delivers?

Scoring is deliberately explainable: every point comes from a named signal,
returned as a reason string. The owner sees WHY a lead scored 80, not just
that it did. Signals are local heuristics over facts the lead produced —
no external data, no bought lists.

Fit model (mirrors the Delivery Ledger + target customer from the site):
- industry match: salon/barbershop/spa/beauty/wellness (core deliverable)
- local market: Kisii/Kenya (where Nexora has presence) or explicit remote
- digital gap: weak/absent website or social-only presence (the pain we fix)
- contactability: WhatsApp/phone/email discoverable (outreach possible)
- intent signals: launching, rebranding, expanding (timing in our favor)
"""

from __future__ import annotations

import re
from typing import Any

# --- signal patterns -------------------------------------------------------
INDUSTRY = re.compile(
    r"\b(salon|barbershop|barber|spa|beauty|nail|hair|wellness|braiding|cosmetic)\w*",
    re.IGNORECASE,
)
LOCAL_MARKET = re.compile(
    r"\b(kisii|kisumu|nairobi|eldoret|nakuru|mombasa|nyamira|keroka|ogembo|kenya)\b",
    re.IGNORECASE,
)
DIGITAL_GAP = re.compile(
    r"\b(no (online |digital )?presence|no website|not online|lacks? a website|"
    r"outdated|old website|facebook only|instagram only|whatsapp only|"
    r"under construction|coming soon)\b", re.IGNORECASE,
)
CONTACT = re.compile(
    r"\b(whatsapp|wa\.me|\+?254\d{9}|0\d{9}|@[\w.]+\.(com|co|ke)|email|phone|call us)\b",
    re.IGNORECASE,
)
INTENT = re.compile(
    r"\b(launching|launched|opening|opened|expanding|new branch|rebrand|"
    r"moving|growth|growing|increasing)\b", re.IGNORECASE,
)

# Points per signal (sums to 100 with all signals present)
WEIGHTS = {
    "industry_match": 30,
    "local_market": 20,
    "digital_gap": 25,
    "contactable": 15,
    "intent_signal": 10,
}

# The lead kinds worth scoring — anything else scores on raw signals only
CORE_INDUSTRIES = ("salon", "barbershop", "spa", "beauty", "wellness")


def score_lead(lead: dict[str, Any]) -> dict[str, Any]:
    """Score a lead 0-100. Returns score + the reasons behind every point."""
    text = " ".join(
        str(lead.get(k, "") or "") for k in ("name", "kind", "location", "notes")
    )
    score = 0
    reasons: list[str] = []

    if INDUSTRY.search(text) or str(lead.get("kind", "")).lower() in CORE_INDUSTRIES:
        score += WEIGHTS["industry_match"]
        reasons.append(f"+{WEIGHTS['industry_match']} core industry "
                       f"({lead.get('kind') or 'beauty/wellness'})")

    if LOCAL_MARKET.search(text) or LOCAL_MARKET.search(str(lead.get("location", ""))):
        score += WEIGHTS["local_market"]
        reasons.append(f"+{WEIGHTS['local_market']} local market "
                       f"({lead.get('location') or 'Kenya'})")

    if DIGITAL_GAP.search(text):
        score += WEIGHTS["digital_gap"]
        hit = DIGITAL_GAP.search(text).group(0)
        reasons.append(f"+{WEIGHTS['digital_gap']} digital gap: '{hit}'")

    if CONTACT.search(text) or lead.get("contact") or lead.get("url"):
        score += WEIGHTS["contactable"]
        reasons.append(f"+{WEIGHTS['contactable']} contactable")

    if INTENT.search(text):
        score += WEIGHTS["intent_signal"]
        hit = INTENT.search(text).group(0)
        reasons.append(f"+{WEIGHTS['intent_signal']} timing signal: '{hit}'")

    if score == 0:
        reasons.append("no matching signals — low priority")

    return {"score": score, "reasons": reasons}


def grade(score: int) -> str:
    """Letter grade for dashboards: A hot, D cold."""
    if score >= 70:
        return "A"
    if score >= 50:
        return "B"
    if score >= 30:
        return "C"
    return "D"
