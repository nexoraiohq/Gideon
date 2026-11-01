"""Briefing — the CEO report Gideon writes for its owner.

Morning briefing: what happened while you slept (sweeps, facts, opportunities),
what needs your decision (approval queue), and how hungry Gideon still is.
Plain text on purpose: readable in the dashboard, in a terminal, or read aloud
(voice comes in Phase 10).

Every claim in a briefing links to evidence — events, facts, sources. A briefing
that can't show its work is a rumor, and Gideon doesn't deal in those.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from gideon.brain import hunger
from gideon.knowledge import store
from gideon.memory import db
from gideon.research import opportunities as opps
from gideon.research import watchlist


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%A, %d %B %Y")


def _since_events(hours: int = 24, kinds: tuple[str, ...] | None = None) -> list[dict]:
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    out = []
    for ev in db.recent_events(limit=500):
        if kinds and ev["kind"] not in kinds:
            continue
        try:
            ts = datetime.fromisoformat(ev["ts"]).timestamp()
        except ValueError:
            continue
        if ts >= cutoff:
            out.append(ev)
    return out


def build_briefing(*, hours: int = 24, opp_limit: int = 10) -> dict[str, Any]:
    """Assemble the morning briefing. Pure read — writes nothing."""
    sweeps = _since_events(hours, kinds=("sweep_complete",))
    research = _since_events(hours, kinds=("research_complete", "research_failed"))
    hungry = hunger.hunger_status()
    watch_terms = [w["term"] for w in watchlist.list_watch()]
    opportunities = opps.detect_opportunities()[:opp_limit]
    pending = store.list_facts(approved=False, limit=100)
    approved_recent = _since_events(hours, kinds=("fact_approved",))

    facts_learned = sum(int(e["payload"].get("facts_learned", 0)) for e in sweeps)
    targets_studied = sum(int(e["payload"].get("studied", 0)) for e in sweeps)
    failures = [e for e in research if e["kind"] == "research_failed"]

    lines: list[str] = [f"Good morning. Here is what happened in the last {hours} hours.", ""]
    lines.append(f"Targets studied: {targets_studied} across {len(sweeps)} sweep(s).")
    lines.append(f"New facts learned: {facts_learned} (all awaiting your approval).")
    if approved_recent:
        lines.append(f"Facts you approved: {len(approved_recent)}.")
    if failures:
        lines.append(f"Targets I could not study: {len(failures)} — "
                     f"{failures[0]['summary']}.")
    if watch_terms:
        lines.append(f"Watch list active: {', '.join(watch_terms)}.")
    lines.append("")

    lines.append(f"Opportunities worth your eyes ({len(opportunities)}):")
    if opportunities:
        for op in opportunities:
            lines.append(f"  - [{op['kind']}] {op['title']} — {op['why']}")
            lines.append(f"    next: {op['suggested_action']}")
    else:
        lines.append("  None detected yet — knowledge base still thin; I keep studying.")
    lines.append("")

    lines.append(f"Needs your decision: {len(pending)} facts in the approval queue.")
    lines.append(hungry["message"])

    return {
        "date": _today(),
        "hours": hours,
        "summary": {
            "sweeps": len(sweeps),
            "targets_studied": targets_studied,
            "facts_learned": facts_learned,
            "facts_pending": len(pending),
            "facts_approved_recent": len(approved_recent),
            "failures": len(failures),
            "opportunities": len(opportunities),
        },
        "opportunities": opportunities,
        "hunger": hungry,
        "text": "\n".join(lines),
    }
