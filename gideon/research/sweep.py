"""Sweep — Gideon's morning pass over everything it studies.

One sweep: every active target is studied (fetch → candidate facts queued for
approval), failures are collected honestly, and the run is audited. This is a
GREEN action — gathering knowledge is autonomous; keeping it stays the owner's.

Scheduler note: `gideon sweep` is the CLI entry; the OS scheduler (Task Scheduler
on Windows) or the /api/sweep endpoint calls it — no daemon needed on a 6 GB box.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from gideon.knowledge import store, targets
from gideon.memory import db


def sweep(target_ids: list[int] | None = None) -> dict[str, Any]:
    """Study active targets once. Returns a run report (never raises on one
    bad target — a dead competitor site must not kill the whole morning)."""
    if target_ids is None:
        target_list = targets.list_targets(active_only=True)
    else:
        target_list = [
            t for tid in target_ids
            if (t := targets.get_target(tid)) is not None and t["active"]
        ]

    studied: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    total_facts = 0

    for target in target_list:
        result = targets.research_target(target["id"])
        if result["ok"]:
            total_facts += len(result["added"])
            studied.append({
                "target_id": target["id"],
                "name": target["name"],
                "facts": len(result["added"]),
                "duplicates": result["skipped"],
            })
        else:
            failed.append({
                "target_id": target["id"],
                "name": target["name"],
                "error": result["error"],
            })

    report = {
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "targets_total": len(target_list),
        "studied": studied,
        "failed": failed,
        "facts_learned": total_facts,
        "facts_pending": store.count_facts(approved=False),
    }
    db.record_event(
        "sweep_complete",
        f"swept {len(studied)}/{len(target_list)} targets, "
        f"{total_facts} new facts awaiting approval",
        {"studied": len(studied), "failed": len(failed),
         "facts_learned": total_facts},
    )
    return report
