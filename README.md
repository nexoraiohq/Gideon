# GIDEON — Nexora Growth Agent 

A Gideon-style AI chief of staff for Nexora Studio: autonomous research, prospecting,
outreach, CEO-style reporting — with data screens, voice, and self-improvement.
Runs locally on Windows.

**Mission:** zero clients → predictable monthly cashflow for Nexora Studio.

## Quick start

```powershell
# 1. Create virtual environment (first time)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 2. Initialize storage + database
python -m gideon.cli init

# 3. Health check (everything should be PASS)
python -m gideon.cli doctor

# 4. Frontend (React + TypeScript) — first time only
cd web
npm install
npm run build        # production build → web/dist (served by FastAPI)
#   or for development with hot reload:
npm run dev          # http://127.0.0.1:5173 (API proxied to :8420)

# 5. Run the dashboard
cd ..
python -m gideon.cli serve   # then open http://127.0.0.1:8420

# 6. Run the test suite (the "nothing breaks" gate)
pytest
```

## Project layout

```
Gideon/
├── gideon/               # source code (the agent itself)
│   ├── config.py         # settings + paths (single source of truth)
│   ├── app.py            # FastAPI dashboard server
│   ├── cli.py            # init | doctor | serve
│   ├── core/             # constitution, decision tiers, guardrails
│   ├── memory/           # database + repositories (all stored state)
│   ├── llm/              # LLM interface (Ollama now, API later)
│   └── modules/          # one package per feature phase
├── config/               # VERSIONED rules & settings (constitution lives in git)
│   ├── settings.yaml     # schedules, channels, autonomy
│   └── constitution.yaml # decision tiers + Delivery Ledger
├── data/                 # ALL runtime storage (git-ignored, except .gitkeep)
│   ├── gideon.db         # SQLite: facts, leads, messages, events, screens…
│   ├── knowledge/        # embeddings / documents
│   ├── reports/          # morning & evening reports (JSON archive)
│   ├── screens/          # saved Gideon Display data screens (JSON)
│   ├── inbox/            # items awaiting owner approval
│   ├── logs/             # append-only logs
│   └── backups/          # database backups
├── web/                  # React + TypeScript dashboard (Vite)
│   ├── src/              # typed components, API client, types
│   ├── dist/             # production build (git-ignored) — served by FastAPI
│   └── index.html        # Vite entry shell
├── tests/                # pytest — must pass before any change ships
├── docs/                 # architecture & decisions
└── GIDEON_BUILD_PLAN.md  # the master plan
```

## Storage rules (scales, nothing breaks)

1. **Constitution in git, memory in data.** Rules (`config/`) are versioned; learned
   facts and history (`data/`) are runtime state, backed up, never hand-edited.
2. **All state in one place:** `data/gideon.db` + `data/` subfolders — nothing writes
   outside `data/`. Change location with `GIDEON_DATA_DIR`.
3. **Append-only:** events, messages, decisions, reports are never overwritten — full
   audit trail, easy rollback of *understanding*, not just code.
4. **Repository layer:** modules access the DB through `gideon.memory.db` only, so the
   engine can later swap SQLite → Postgres without touching feature code.
5. **Tests gate everything:** `pytest` must pass before any commit; `git revert` is
   the undo button.
6. **Modules are independent:** each feature lives in `gideon/modules/<name>/` and
   talks to `core/` + `memory/` — adding a phase never rewrites another.

## Commands

| Command | Purpose |
|---|---|
| `python -m gideon.cli init` | Create data folders + initialize database |
| `python -m gideon.cli doctor` | Health check: env, storage, config, LLM, git |
| `python -m gideon.cli serve` | Run the dashboard (http://127.0.0.1:8420) |
| `cd web && npm run dev` | Frontend dev server with hot reload (:5173) |
| `cd web && npm run build` | Type-check + build React app to `web/dist` |
| `pytest` | Run the full test suite |
