"""Leads repository + the finder — turning knowledge into a pipeline.

find_leads() mines the knowledge base for named businesses (the ones the
opportunity detector flagged: weak digital, missing booking, local signals),
scores each one, and stores qualified prospects with their reasons attached.

Everything is traceable: every lead keeps the source_url of the fact that
produced it and the score's reason list. No bought lists, no invented names.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from gideon.knowledge import store
from gideon.memory import db
from gideon.research import opportunities as opps
from gideon.sales import scoring

# Business-name pattern: Capitalized words before an industry noun
# e.g. "Mama Nzuri Salon", "Glow Beauty Bar", "Style Point Barbershop"
_NAME_BEFORE = re.compile(
    r"\b((?:[A-Z][\w']*(?:\s+[A-Z][\w']*){0,3})\s+"
    r"(?:Salon|Barbershop|Barber|Spa|Beauty|Nails?|Hair|Wellness|Braiding|Studio))"
    r"\b"
)
# Also: "X is a salon in Y" style
_NAME_IS_A = re.compile(
    r"\b([A-Z][\w']*(?:\s+[A-Z][\w']*){0,2})\s+is\s+a?\s*"
    r"(salon|barbershop|spa|beauty (?:bar|shop|parlor)|nail (?:bar|studio)|hair (?:studio|salon))",
    re.IGNORECASE,
)
_LOCATION_AFTER = re.compile(
    r"\b(?:in|at|near|located in)\s+((?:[A-Z][\w']*\s*){1,3})(?:,|\.|$| (?:and|with|that|which))",
)
_KENYA_TOWNS = re.compile(
    r"\b(kisii|kisumu|nairobi|eldoret|nakuru|mombasa|nyamira|keroka|ogembo)\b", re.IGNORECASE
)

# Words that never appear in a real business name — they signal marketing copy
# ("Salon Websites", "Barbershop Website Design") rather than a named prospect
_JUNK_WORDS = {
    "website", "websites", "web", "design", "site", "sites", "page", "pages",
    "best", "top", "cheap", "free", "services", "service", "for", "the",
    "kenya", "online", "template", "templates", "examples", "example",
}

# Never prospect ourselves
_OWN_NAMES = {"nexora", "nexora studio", "nexoraio"}

# Businesses Nexora already works with (case studies / existing clients).
# They are served, not pitched. Phase 9 will promote this to a data table.
EXISTING_CLIENTS = {"states barbershop"}


# Industry words that carry no name value — a "name" made only of these is
# marketing copy or a fragment ("Hair Salon"), not a business ("Hair Salon Studio" is)
_INDUSTRY_WORDS = {
    "salon", "saloon", "barbershop", "barber", "spa", "beauty", "nail", "nails",
    "hair", "wellness", "braiding", "studio", "shop", "parlour", "boutique",
}


def _is_real_name(name: str) -> bool:
    lowered = name.lower().strip()
    lowered = re.sub(r"^the\s+", "", lowered)  # "The Salon" is a fragment, "The Ultimate Spa" is not
    if lowered in _OWN_NAMES or lowered in EXISTING_CLIENTS:
        return False
    words = lowered.split()
    if not words or len(words) > 5:
        return False
    # any junk word disqualifies — real salons are named "Glow", not "Salon Websites"
    if any(w in _JUNK_WORDS for w in words):
        return False
    # must contain at least one word that isn't just "salon/spa/hair/and" etc.
    # — "Spa and Barbershop" is a fragment, "Mama Nzuri Salon" is a business
    if not any(w not in _INDUSTRY_WORDS and w != "and" for w in words):
        return False
    # a real name never starts with a connector ("and Hair Salon" = fragment)
    return words[0] not in {"and", "or", "of", "the", "for", "with"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def extract_businesses(text: str) -> list[dict[str, str]]:
    """Pull named beauty-industry businesses + locations out of text."""
    found: dict[str, dict[str, str]] = {}

    for match in _NAME_BEFORE.finditer(text):
        name = match.group(1).strip()
        if _is_real_name(name):
            found[name.lower()] = {"name": name, "kind": _kind_of(name), "location": ""}

    for match in _NAME_IS_A.finditer(text):
        name = match.group(1).strip()
        # len > 2 filters "It is a salon"; junk filter drops marketing copy
        if len(name) > 2 and _is_real_name(name):
            found.setdefault(
                name.lower(),
                {"name": name, "kind": match.group(2).lower(), "location": ""},
            )

    # Attach locations: nearest town mention after the business name
    for key, biz in found.items():
        idx = text.lower().find(key)
        if idx == -1:
            continue
        window = text[idx: idx + 200]
        town = _KENYA_TOWNS.search(window)
        if town:
            biz["location"] = town.group(1).capitalize()
        else:
            loc = _LOCATION_AFTER.search(window)
            if loc:
                biz["location"] = loc.group(1).strip()

    return list(found.values())


def _kind_of(name: str) -> str:
    lowered = name.lower()
    for word in ("barbershop", "barber", "salon", "spa", "beauty", "nail", "hair",
                 "wellness", "braiding", "studio"):
        if word in lowered:
            return word
    return "business"


def add_lead(
    name: str,
    kind: str = "business",
    location: str = "",
    url: str | None = None,
    contact: str = "",
    source_url: str | None = None,
    notes: str = "",
) -> int:
    """Store a lead (scored at insert — the reasons ride along)."""
    name = name.strip()
    if not name:
        raise ValueError("lead needs a name")
    result = scoring.score_lead(
        {"name": name, "kind": kind, "location": location, "url": url,
         "contact": contact, "notes": notes}
    )
    now = _now()
    conn = db.get_connection()
    cur = conn.execute(
        "INSERT INTO leads(name, kind, location, url, contact, source_url, score, "
        "reasons, stage, notes, created_at, updated_at) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?, ?)",
        (name, kind, location, url, contact, source_url, result["score"],
         json.dumps(result["reasons"]), notes, now, now),
    )
    conn.commit()
    lead_id = int(cur.lastrowid)
    db.record_event(
        "lead_found", f"new lead: {name} (score {result['score']})",
        {"lead_id": lead_id, "name": name, "score": result["score"],
         "reasons": result["reasons"]},
    )
    return lead_id


def get_lead(lead_id: int) -> dict[str, Any] | None:
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    return _decode(dict(row)) if row else None


def list_leads(*, stage: str | None = None, min_score: int = 0,
               limit: int = 200) -> list[dict[str, Any]]:
    conn = db.get_connection()
    sql = "SELECT * FROM leads WHERE score >= ?"
    params: list[Any] = [min_score]
    if stage:
        sql += " AND stage = ?"
        params.append(stage)
    rows = conn.execute(
        sql + " ORDER BY score DESC, id DESC LIMIT ?", (*params, limit)
    ).fetchall()
    return [_decode(dict(r)) for r in rows]


def find_leads(*, min_score: int = 30, limit: int = 50) -> dict[str, Any]:
    """Mine knowledge → named businesses → scored leads (deduped by name).

    min_score keeps low-signal noise out of the pipeline; the owner can lower
    it via the API when they want a wider net.
    """
    existing = {
        str(row["name"]).lower()
        for row in db.get_connection().execute("SELECT name FROM leads")
    }

    candidates: dict[str, dict[str, Any]] = {}
    for fact in store.list_facts(limit=2000):
        for biz in extract_businesses(fact["content"]):
            key = biz["name"].lower()
            entry = candidates.setdefault(
                key, {**biz, "source_url": fact["source_url"], "notes": fact["content"]}
            )
            # accumulate location if a later fact has it and we don't
            if not entry.get("location") and biz.get("location"):
                entry["location"] = biz["location"]

    added: list[dict[str, Any]] = []
    skipped_existing = 0
    below_threshold = 0
    for key, biz in candidates.items():
        if key in existing:
            skipped_existing += 1
            continue
        preview = scoring.score_lead({**biz, "notes": biz.get("notes", "")})
        if preview["score"] < min_score:
            below_threshold += 1
            continue
        lead_id = add_lead(
            biz["name"], biz["kind"], biz.get("location", ""),
            source_url=biz.get("source_url"), notes=str(biz.get("notes", ""))[:400],
        )
        added.append({"id": lead_id, **biz, "score": preview["score"],
                      "reasons": preview["reasons"]})

    report = {
        "candidates": len(candidates),
        "added": added,
        "skipped_existing": skipped_existing,
        "below_threshold": below_threshold,
    }
    db.record_event(
        "lead_sweep",
        f"lead finder: {len(added)} new leads "
        f"({skipped_existing} already known, {below_threshold} below score {min_score})",
        {"added": len(added), "candidates": len(candidates)},
    )
    return report


def _decode(row: dict[str, Any]) -> dict[str, Any]:
    try:
        row["reasons"] = json.loads(row.get("reasons") or "[]")
    except (TypeError, ValueError):
        row["reasons"] = []
    row["grade"] = scoring.grade(int(row.get("score", 0)))
    return row
