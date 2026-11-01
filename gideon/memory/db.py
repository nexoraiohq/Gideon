"""SQLite storage engine + repository layer.

Why a repository layer: all modules touch the DB *through this file* only, so we can
later swap SQLite → Postgres (or add FTS/embeddings) without rewriting features.

Rules:
- Append-only by default: events/messages/decisions are inserted, never updated away.
- Schema changes go through migrations (schema_migrations table) — never hand-ALTER.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from gideon.config import get_settings

_local = threading.local()

# Ordered migrations: (version, sql)
MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );

        -- Every important thing that happens (audit trail, append-only)
        CREATE TABLE IF NOT EXISTS events (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ts         TEXT NOT NULL,
            kind       TEXT NOT NULL,
            summary    TEXT NOT NULL DEFAULT '',
            payload    TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_events_kind_ts ON events(kind, ts);

        -- Facts learned from targets (source + date always kept)
        CREATE TABLE IF NOT EXISTS facts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            content    TEXT NOT NULL,
            category   TEXT NOT NULL DEFAULT 'general',
            source_url TEXT,
            learned_at TEXT NOT NULL,
            approved   INTEGER NOT NULL DEFAULT 0
        );

        -- Saved Gideon Display screens (JSON specs rendered by the dashboard)
        CREATE TABLE IF NOT EXISTS screens (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            kind       TEXT NOT NULL,
            title      TEXT NOT NULL,
            spec       TEXT NOT NULL
        );
        """,
    ),
    (
        2,
        """
        -- Research targets: competitors, markets, prospects Gideon studies
        CREATE TABLE IF NOT EXISTS targets (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT NOT NULL,
            url              TEXT NOT NULL,
            kind             TEXT NOT NULL DEFAULT 'competitor',
            notes            TEXT NOT NULL DEFAULT '',
            active           INTEGER NOT NULL DEFAULT 1,
            created_at       TEXT NOT NULL,
            last_researched  TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_targets_active ON targets(active);
        """,
    ),
    (
        3,
        """
        -- Watch list: subjects/terms Gideon watches across everything it studies
        CREATE TABLE IF NOT EXISTS watchlist (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            term       TEXT NOT NULL,
            note       TEXT NOT NULL DEFAULT '',
            active     INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """,
    ),
    (
        4,
        """
        -- Leads: prospects Gideon found and scored (pipeline = tiny CRM)
        CREATE TABLE IF NOT EXISTS leads (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            kind       TEXT NOT NULL DEFAULT 'business',
            location   TEXT NOT NULL DEFAULT '',
            url        TEXT,
            contact    TEXT NOT NULL DEFAULT '',
            source_url TEXT,
            score      INTEGER NOT NULL DEFAULT 0,
            reasons    TEXT NOT NULL DEFAULT '[]',
            stage      TEXT NOT NULL DEFAULT 'new',
            notes      TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage);
        CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score);
        """,
    ),
]


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")      # concurrent reads, safer writes
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Self-heal: apply PENDING migrations on first connection (fresh or old DB)."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )"""
    )
    applied = {
        row["version"]
        for row in conn.execute("SELECT version FROM schema_migrations")
    }
    for version, sql in MIGRATIONS:
        if version in applied:
            continue
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)",
            (version, _now()),
        )
    conn.commit()


def get_connection() -> sqlite3.Connection:
    """Thread-local connection to the configured database."""
    conn = getattr(_local, "conn", None)
    db_path = get_settings().db_path
    if conn is None or getattr(_local, "db_path", None) != db_path:
        if conn is not None:
            conn.close()
        conn = _connect(db_path)
        _ensure_schema(conn)
        _local.conn = conn
        _local.db_path = db_path
    return conn


def close_connection() -> None:
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None
        _local.db_path = None


def init_db(db_path: Path | None = None) -> list[int]:
    """Apply pending migrations. Returns list of versions applied."""
    conn = _connect(db_path or get_settings().db_path)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )"""
        )
        applied = {
            row["version"]
            for row in conn.execute("SELECT version FROM schema_migrations")
        }
        ran: list[int] = []
        for version, sql in MIGRATIONS:
            if version in applied:
                continue
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)",
                (version, _now()),
            )
            conn.commit()
            ran.append(version)
        return ran
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_event(kind: str, summary: str = "", payload: dict | None = None) -> int:
    """Append an event to the audit trail. Returns event id."""
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO events(ts, kind, summary, payload) VALUES(?, ?, ?, ?)",
        (_now(), kind, summary, json.dumps(payload or {}, ensure_ascii=False)),
    )
    conn.commit()
    return int(cur.lastrowid)


def recent_events(limit: int = 20, kind: str | None = None) -> list[dict[str, Any]]:
    conn = get_connection()
    if kind:
        rows = conn.execute(
            "SELECT * FROM events WHERE kind = ? ORDER BY id DESC LIMIT ?",
            (kind, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        item["payload"] = json.loads(item["payload"] or "{}")
        out.append(item)
    return out


def save_screen(kind: str, title: str, spec: dict) -> int:
    """Persist a Gideon Display screen spec; also mirror to data/screens/ as JSON."""
    settings = get_settings()
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO screens(created_at, kind, title, spec) VALUES(?, ?, ?, ?)",
        (_now(), kind, title, json.dumps(spec, ensure_ascii=False)),
    )
    conn.commit()
    screen_id = int(cur.lastrowid)
    settings.screens_dir.mkdir(parents=True, exist_ok=True)
    path = settings.screens_dir / f"screen_{screen_id:06d}.json"
    path.write_text(
        json.dumps(
            {"id": screen_id, "created_at": _now(), "kind": kind, "title": title,
             "spec": spec},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return screen_id


def list_screens(limit: int = 50) -> list[dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, created_at, kind, title FROM screens ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def healthcheck() -> dict[str, Any]:
    """Cheap DB probe used by doctor + /api/health."""
    try:
        conn = get_connection()
        conn.execute("SELECT 1").fetchone()
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        return {"ok": True, "tables": sorted(tables), "path": str(get_settings().db_path)}
    except Exception as exc:  # pragma: no cover - surfaced to doctor
        return {"ok": False, "error": str(exc)}
