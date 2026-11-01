"""Watch list — subjects Gideon tracks everywhere it looks.

A watch entry is a term ("booking flow", "pricing", "Kisii") that the opportunity
detector hunts for in every fact Gideon learns. Adding/removing watch terms is
GREEN (learning is autonomous); the watch list shapes what counts as an
opportunity, so it's part of the constitution's knowledge domain, not outreach.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from gideon.memory import db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def add_watch(term: str, note: str = "") -> int:
    term = term.strip().lower()
    if not term:
        raise ValueError("watch term cannot be empty")
    conn = db.get_connection()
    # Re-activating an existing term beats duplicating it
    row = conn.execute(
        "SELECT id FROM watchlist WHERE term = ?", (term,)
    ).fetchone()
    if row:
        conn.execute("UPDATE watchlist SET active = 1 WHERE id = ?", (row["id"],))
        conn.commit()
        return int(row["id"])
    cur = conn.execute(
        "INSERT INTO watchlist(term, note, active, created_at) VALUES(?, ?, 1, ?)",
        (term, note, _now()),
    )
    conn.commit()
    db.record_event("watch_added", f"watching for '{term}'", {"term": term})
    return int(cur.lastrowid)


def remove_watch(watch_id: int) -> bool:
    conn = db.get_connection()
    cur = conn.execute("UPDATE watchlist SET active = 0 WHERE id = ?", (watch_id,))
    conn.commit()
    if cur.rowcount:
        db.record_event("watch_removed", f"stopped watching #{watch_id}",
                        {"watch_id": watch_id})
    return bool(cur.rowcount)


def list_watch(*, active_only: bool = True) -> list[dict[str, Any]]:
    conn = db.get_connection()
    sql = "SELECT * FROM watchlist"
    if active_only:
        sql += " WHERE active = 1"
    return [dict(r) for r in conn.execute(sql + " ORDER BY id").fetchall()]


# Convenience alias used by research/__init__.py
watch = add_watch
