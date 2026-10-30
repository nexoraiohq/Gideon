# Gideon — Architecture

## Why it scales
1. **Constitution in git, memory in data.** Rules (`config/`) are code-reviewed and
   versioned; learned facts/state (`data/`) are runtime and backed up.
2. **Repository layer** (`gideon/memory/db.py`) is the only DB door — SQLite today,
   Postgres tomorrow, no feature code changes.
3. **LLM behind an interface** (`gideon/llm/`) — Ollama now, hybrid API later.
4. **One package per feature** (`gideon/modules/<phase>/`) — adding a phase never
   rewrites another; each ships with its own tests.
5. **Append-only audit trail** — events, messages, decisions, reports are inserts,
   never silent overwrites: full history of what Gideon did and why.

## Why nothing breaks
- `pytest` is the ship gate: green or no commit.
- Migrations are ordered and idempotent (`schema_migrations`) — restarts never re-apply.
- `python -m gideon.cli doctor` = one-command health check (storage, DB, config, LLM, git).
- Runtime writes are confined to `GIDEON_DATA_DIR` (default `data/`) — tests run against
  throwaway dirs, so the suite can never corrupt real memory.
- Git = instant rollback for code; `data/backups/` = DB snapshots (Phase 3 adds the job).

## Frontend (React + TypeScript)

`web/` is a Vite + React 19 + strict TypeScript app:
- **Dev:** `npm run dev` → :5173 with `/api` proxied to FastAPI :8420 (hot reload)
- **Prod:** `npm run build` → `web/dist`, served by FastAPI at :8420 (single origin)
- `src/types.ts` mirrors API contracts; `src/api.ts` is the only fetch layer —
  the backend stays the single source of truth for shapes.
- Phase 7 (Gideon Display) renders chart/table/evidence blocks as React components.

## Storage map
| Where | What | Versioned? |
|---|---|---|
| `config/settings.yaml` | schedules, caps, autonomy | git ✅ |
| `config/constitution.yaml` | decision tiers + Delivery Ledger | git ✅ |
| `data/gideon.db` | events, facts, screens, (later: leads, messages, decisions) | backup |
| `data/knowledge/` | documents + embeddings | backup |
| `data/reports/` | morning/evening briefings (JSON) | backup |
| `data/screens/` | Gideon Display screen specs (JSON) | backup |
| `data/inbox/` | items awaiting owner approval | backup |
| `data/logs/` | append-only logs | rotating |

## The Gideon Display contract (Phase 7)
A "screen" is a JSON spec: `{kind, title, blocks:[chart|table|evidence|metrics|reasoning]}`.
Stored in DB + mirrored to `data/screens/`. Reports reference screen ids so any briefing
can re-pull its data — "pull up the screen" is just `GET /api/screens/<id>`.
