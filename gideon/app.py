"""Gideon dashboard server (FastAPI).

Serves:
- /                React + TypeScript dashboard (built from web/ → web/dist)
- /api/health      full health probe (storage, DB, constitution, LLM)
- /api/events      recent audit-trail events
- /api/screens     saved data screens

Frontend lives in web/ (Vite + React + TS):
  dev   → cd web && npm run dev    (http://127.0.0.1:5173, /api proxied here)
  build → cd web && npm run build  (web/dist served here at :8420)
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from gideon import __version__
from gideon.config import WEB_DIR, get_settings
from gideon.core import constitution
from gideon.llm import ollama_status
from gideon.memory import db

app = FastAPI(title="Gideon", version=__version__)

DIST_DIR = WEB_DIR / "dist"
if (DIST_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")


@app.get("/api/health")
def health() -> JSONResponse:
    settings = get_settings()
    probe = db.healthcheck()
    body = {
        "status": "ok" if probe.get("ok") else "degraded",
        "version": __version__,
        "data_dir": str(settings.data_dir),
        "database": probe,
        "constitution": {
            "version": constitution.load_constitution().get("version", "unknown"),
            "autonomy": constitution.autonomy_level(),
            "ledger_claims": len(constitution.ledger_claims()),
        },
        "llm": ollama_status(),
    }
    return JSONResponse(body, status_code=200 if probe.get("ok") else 503)


@app.get("/api/events")
def events(limit: int = 20, kind: str | None = None) -> JSONResponse:
    return JSONResponse(db.recent_events(limit=limit, kind=kind))


@app.get("/api/screens")
def screens(limit: int = 50) -> JSONResponse:
    return JSONResponse(db.list_screens(limit=limit))


@app.get("/")
def index():  # no response annotation: mixed Response types, FastAPI skips model
    page = DIST_DIR / "index.html"
    if not page.exists():
        return JSONResponse(
            {
                "detail": "Frontend not built yet — run: "
                          "cd web && npm install && npm run build "
                          "(or npm run dev for development)"
            },
            status_code=404,
        )
    return FileResponse(page)


def run(host: str = "127.0.0.1", port: int = 8420) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="warning")
