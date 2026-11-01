"""Targets + the learning loop — Gideon's hunger with direction.

A target is anything Gideon studies on its own: a competitor site, a market page,
a prospect's website. Adding a target is GREEN (learning_is_green trait); the
loop is: fetch → facts land UNAPPROVED → owner approves → long-term memory.

The loop NEVER writes approved facts itself. Collection is autonomous;
commitment is the owner's. That boundary is the constitution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from gideon.brain import hunger
from gideon.knowledge import ingest, store
from gideon.memory import db

TARGET_KINDS = ("competitor", "market", "prospect", "resource")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def add_target(name: str, url: str, kind: str = "competitor", notes: str = "") -> int:
    name, url = name.strip(), url.strip()
    if not name or not url:
        raise ValueError("target needs both a name and a url")
    if not url.startswith(("http://", "https://")):
        raise ValueError("url must start with http:// or https://")
    if kind not in TARGET_KINDS:
        raise ValueError(f"kind must be one of {TARGET_KINDS}")
    conn = db.get_connection()
    cur = conn.execute(
        "INSERT INTO targets(name, url, kind, notes, active, created_at) "
        "VALUES(?, ?, ?, ?, 1, ?)",
        (name, url, kind, notes, _now()),
    )
    conn.commit()
    target_id = int(cur.lastrowid)
    db.record_event("target_added", f"will study {name} ({kind})", {
        "target_id": target_id, "url": url, "kind": kind,
    })
    return target_id


def list_targets(*, active_only: bool = True) -> list[dict[str, Any]]:
    conn = db.get_connection()
    sql = "SELECT * FROM targets"
    if active_only:
        sql += " WHERE active = 1"
    return [dict(r) for r in conn.execute(sql + " ORDER BY id").fetchall()]


def get_target(target_id: int) -> dict[str, Any] | None:
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM targets WHERE id = ?", (target_id,)).fetchone()
    return dict(row) if row else None


def pause_target(target_id: int) -> bool:
    conn = db.get_connection()
    cur = conn.execute("UPDATE targets SET active = 0 WHERE id = ?", (target_id,))
    conn.commit()
    if cur.rowcount:
        db.record_event("target_paused", f"paused target #{target_id}",
                        {"target_id": target_id})
    return bool(cur.rowcount)


def resume_target(target_id: int) -> bool:
    conn = db.get_connection()
    cur = conn.execute("UPDATE targets SET active = 1 WHERE id = ?", (target_id,))
    conn.commit()
    if cur.rowcount:
        db.record_event("target_resumed", f"resumed target #{target_id}",
                        {"target_id": target_id})
    return bool(cur.rowcount)


def mark_researched(target_id: int) -> None:
    conn = db.get_connection()
    conn.execute("UPDATE targets SET last_researched = ? WHERE id = ?", (_now(), target_id))
    conn.commit()


def research_target(target_id: int) -> dict[str, Any]:
    """Run the learning loop once for a target: fetch → candidate facts (pending).

    Facts land unapproved; the owner decides what becomes memory. Failures are
    reported, never silently swallowed — Gideon reports honestly.
    """
    target = get_target(target_id)
    if target is None:
        raise ValueError(f"target #{target_id} not found")
    if not target["active"]:
        raise ValueError(f"target #{target_id} is paused")

    try:
        result = ingest.ingest_url(target["url"], approved=False)
    except Exception as exc:
        db.record_event("research_failed", f"could not study {target['name']}", {
            "target_id": target_id, "error": str(exc),
        })
        return {"target_id": target_id, "ok": False, "error": str(exc),
                "added": [], "skipped": 0}

    mark_researched(target_id)
    db.record_event(
        "research_complete",
        f"studied {target['name']}: {len(result['added'])} new facts awaiting approval",
        {"target_id": target_id, "added": len(result["added"]),
         "skipped": result["skipped"]},
    )
    return {"target_id": target_id, "ok": True, "added": result["added"],
            "skipped": result["skipped"], "chars": result["chars"]}


def approval_queue(limit: int = 100) -> list[dict[str, Any]]:
    """Unapproved facts waiting on the owner — the single review surface."""
    return store.list_facts(approved=False, limit=limit)


def hunger_report() -> dict[str, Any]:
    """What Gideon is studying + what awaits approval — for morning briefings."""
    status = hunger.hunger_status()
    return {
        "hunger": status,
        "active_targets": len(list_targets(active_only=True)),
        "pending_approvals": store.count_facts(approved=False),
        "approved_facts": store.count_facts(approved=True),
    }
