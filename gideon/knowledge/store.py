"""Facts store — the repository layer over the `facts` table.

Rules (mirrors the constitution):
- Every fact keeps its source_url and learned_at — knowledge without provenance
  is rumor, not knowledge.
- Facts land UNAPPROVED. The owner (or later, an earned-autonomy rule) approves;
  only approved facts feed answers and outreach copy. This is the approval gate.
- Retrieval is local token-overlap scoring — simple, dependency-free, fast on
  thousands of facts. Gideon's own embeddings upgrade this in a later phase.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from gideon.memory import db

_WORD = re.compile(r"[a-z0-9]+")

# Words too common to identify a topic (retrieval noise)
STOPWORDS = frozenset(
    "a an and are as at be by for from has have in is it its of on or that the "
    "to was we with your you our us not no do does did can will would should".split()
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def tokenize(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if w not in STOPWORDS]


def add_fact(
    content: str,
    category: str = "general",
    source_url: str | None = None,
    *,
    approved: bool = False,
) -> int:
    """Store a fact. Unapproved by default — the gate is the default."""
    content = " ".join(content.split())
    if not content:
        raise ValueError("fact content cannot be empty")
    conn = db.get_connection()
    cur = conn.execute(
        "INSERT INTO facts(content, category, source_url, learned_at, approved) "
        "VALUES(?, ?, ?, ?, ?)",
        (content, category, source_url, _now(), 1 if approved else 0),
    )
    conn.commit()
    return int(cur.lastrowid)


def approve_fact(fact_id: int) -> bool:
    """Owner approves a fact — it may now feed answers and outreach."""
    conn = db.get_connection()
    cur = conn.execute(
        "UPDATE facts SET approved = 1 WHERE id = ? AND approved = 0", (fact_id,)
    )
    conn.commit()
    if cur.rowcount:
        db.record_event("fact_approved", f"approved fact #{fact_id}", {"fact_id": fact_id})
    return bool(cur.rowcount)


def get_fact(fact_id: int) -> dict[str, Any] | None:
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
    return dict(row) if row else None


def list_facts(*, approved: bool | None = None, limit: int = 200) -> list[dict[str, Any]]:
    conn = db.get_connection()
    if approved is None:
        rows = conn.execute(
            "SELECT * FROM facts ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM facts WHERE approved = ? ORDER BY id DESC LIMIT ?",
            (1 if approved else 0, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def count_facts(*, approved: bool | None = None) -> int:
    conn = db.get_connection()
    if approved is None:
        row = conn.execute("SELECT COUNT(*) AS n FROM facts").fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM facts WHERE approved = ?",
            (1 if approved else 0,),
        ).fetchone()
    return int(row["n"])


def search_facts(query: str, *, approved_only: bool = True, limit: int = 5) -> list[dict]:
    """Rank facts by token overlap with the query. Local, cheap, cited.

    Scoring: fraction of query tokens present in the fact (0..1), so a fact
    matching every query word outranks one matching a single common word.
    """
    q_tokens = set(tokenize(query))
    if not q_tokens:
        return []
    conn = db.get_connection()
    sql = "SELECT * FROM facts"
    params: tuple = ()
    if approved_only:
        sql += " WHERE approved = 1"
    rows = conn.execute(sql + " ORDER BY id DESC LIMIT 5000", params).fetchall()

    scored: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        fact = dict(row)
        f_tokens = set(tokenize(fact["content"]))
        if not f_tokens:
            continue
        overlap = len(q_tokens & f_tokens)
        if overlap:
            scored.append((overlap / len(q_tokens), fact))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [fact for _, fact in scored[:limit]]
