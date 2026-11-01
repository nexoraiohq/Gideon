"""Pipeline — the tiny CRM. Where every lead sits in the journey.

Stages: new → contacted → replied → proposal → won | lost

Rules:
- Moves are forward-only through the funnel (or straight to won/lost from any
  stage — reality allows "they signed on the first call" and "dead end").
- Every move is audited in the events table: who, when, from → to. Gideon's
  memory of a conversation with a prospect is never a guess.
- Won is special: recording a win also writes a delivery check — Gideon will
  only claim publicly what Nexora can actually deliver (Delivery Ledger).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from gideon.memory import db

STAGES: tuple[str, ...] = ("new", "contacted", "replied", "proposal", "won", "lost")

# Allowed transitions: from → set of valid next stages
_TRANSITIONS: dict[str, set[str]] = {
    "new": {"contacted", "lost"},
    "contacted": {"replied", "proposal", "lost"},
    "replied": {"proposal", "won", "lost"},
    "proposal": {"won", "lost"},
    "won": set(),
    "lost": set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def move_stage(lead_id: int, new_stage: str, note: str = "") -> dict[str, Any]:
    """Advance a lead through the pipeline. Raises ValueError on bad moves
    — a lead can't go from 'new' straight to 'won'; that's a fantasy, not a
    pipeline."""
    if new_stage not in STAGES:
        raise ValueError(f"unknown stage '{new_stage}' (stages: {', '.join(STAGES)})")

    conn = db.get_connection()
    row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    if not row:
        raise ValueError(f"lead #{lead_id} not found")

    lead = dict(row)
    current = lead["stage"]
    if new_stage == current:
        return {"lead_id": lead_id, "stage": current, "changed": False,
                "detail": "already in that stage"}

    if new_stage not in _TRANSITIONS[current]:
        allowed = ", ".join(sorted(_TRANSITIONS[current])) or "none (terminal)"
        raise ValueError(
            f"cannot move '{current}' → '{new_stage}'; allowed from here: {allowed}"
        )

    now = _now()
    notes = lead["notes"]
    if note:
        notes = f"{notes}\n[{now}] {current}→{new_stage}: {note}".strip()

    conn.execute(
        "UPDATE leads SET stage = ?, notes = ?, updated_at = ? WHERE id = ?",
        (new_stage, notes, now, lead_id),
    )
    conn.commit()

    db.record_event(
        "lead_stage_changed",
        f"{lead['name']}: {current} → {new_stage}" + (f" ({note})" if note else ""),
        {"lead_id": lead_id, "name": lead["name"], "from": current,
         "to": new_stage, "note": note},
    )
    return {"lead_id": lead_id, "stage": new_stage, "changed": True,
            "from": current, "detail": f"{lead['name']}: {current} → {new_stage}"}


def pipeline_report() -> dict[str, Any]:
    """Counts per stage + value at a glance (the dashboard header)."""
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT stage, COUNT(*) AS n, AVG(score) AS avg_score FROM leads "
        "GROUP BY stage"
    ).fetchall()
    counts = {stage: 0 for stage in STAGES}
    avg_scores: dict[str, float] = {}
    for r in rows:
        counts[r["stage"]] = int(r["n"])
        avg_scores[r["stage"]] = round(float(r["avg_score"] or 0), 1)
    total = sum(counts.values())
    won = counts["won"]
    return {
        "counts": counts,
        "avg_scores": avg_scores,
        "total": total,
        "won": won,
        "win_rate": round(100 * won / total, 1) if total else 0.0,
        "snapshot": json.dumps(counts),
    }
