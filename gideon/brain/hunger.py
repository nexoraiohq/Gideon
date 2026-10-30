"""Hunger — Gideon's built-in drive to always seek knowledge.

Trait (config/constitution.yaml → traits.hungry_for_knowledge):
research and intake are DEFAULT behavior — it never waits to be told. The approval
gate still governs what is *kept* in long-term memory; hunger only controls *seeking*.

Measures daily knowledge intake against floors from config/settings.yaml → hunger.*.
Reports a Gideon-style status line for briefings, and tracks when the brain should
"eat again" (continued training on newly approved material).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from gideon.config import get_settings
from gideon.memory import db


def record_intake(source: str, chars: int, *, kind: str = "web") -> int:
    """Log that Gideon learned something (append-only audit event)."""
    return db.record_event(
        "knowledge_intake",
        f"learned {chars:,} chars from {source}",
        {"source": source, "chars": int(chars), "kind": kind},
    )


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def hunger_status(today: str | None = None) -> dict[str, Any]:
    """Intake vs. floors for the current day — drives the hungry/fed report."""
    settings = get_settings()
    min_items = int(settings.get("hunger.min_items_per_day", 5))
    min_chars = int(settings.get("hunger.min_chars_per_day", 8000))
    day = today or _today_utc()

    items = 0
    chars = 0
    for ev in db.recent_events(limit=1000, kind="knowledge_intake"):
        if ev["ts"].startswith(day):
            items += 1
            chars += int(ev["payload"].get("chars", 0))

    hungry = items < min_items or chars < min_chars
    if hungry:
        message = (
            f"Hungry: {items}/{min_items} items, {chars:,}/{min_chars:,} chars "
            f"today — I will keep studying."
        )
    else:
        message = (
            f"Knowledge intake satisfied today ({items} items, {chars:,} chars). "
            f"Hunger resets at midnight UTC."
        )
    return {
        "day": day,
        "items": items,
        "chars": chars,
        "min_items": min_items,
        "min_chars": min_chars,
        "hungry": hungry,
        "message": message,
    }


def should_retrain(new_chars: int) -> bool:
    """True when enough NEW knowledge has arrived for the brain to eat again."""
    threshold = int(get_settings().get("hunger.retrain_after_new_chars", 20_000))
    return new_chars >= threshold


def retrain_message(new_chars: int) -> str:
    threshold = int(get_settings().get("hunger.retrain_after_new_chars", 20_000))
    return f"The brain has {new_chars:,} new chars — feeding threshold is {threshold:,}."
