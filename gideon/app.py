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
from gideon.core import constitution, guardrail
from gideon.knowledge import answer as knowledge_answer
from gideon.knowledge import store as knowledge_store
from gideon.knowledge import targets as knowledge_targets
from gideon.llm import ollama_status
from gideon.research import briefing as research_briefing
from gideon.research import opportunities as research_opportunities
from gideon.research import sweep as research_sweep
from gideon.research import watchlist as research_watchlist
from gideon.sales import leads as sales_leads
from gideon.sales import pipeline as sales_pipeline
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


# ---------------------------------------------------------------------------
# Phase 2 — Identity: knowledge, cited answers, promise guardrail
# ---------------------------------------------------------------------------
from pydantic import BaseModel  # noqa: E402


class Question(BaseModel):
    question: str


class DraftText(BaseModel):
    text: str


@app.post("/api/ask")
def ask(body: Question) -> JSONResponse:
    """Answer from approved knowledge — always with citations."""
    try:
        return JSONResponse(knowledge_answer.answer(body.question))
    except ValueError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)


@app.get("/api/facts")
def facts(approved: bool | None = None, limit: int = 100) -> JSONResponse:
    items = knowledge_store.list_facts(approved=approved, limit=limit)
    return JSONResponse(
        {"items": items,
         "total": knowledge_store.count_facts(approved=approved),
         "pending": knowledge_store.count_facts(approved=False)}
    )


@app.post("/api/facts/{fact_id}/approve")
def approve(fact_id: int) -> JSONResponse:
    ok = knowledge_store.approve_fact(fact_id)
    if not ok:
        return JSONResponse({"detail": "fact not found or already approved"},
                            status_code=404)
    return JSONResponse({"approved": True, "fact_id": fact_id})


@app.post("/api/check")
def check(body: DraftText) -> JSONResponse:
    """Promise guardrail: judge a draft against the Delivery Ledger."""
    return JSONResponse(guardrail.check_draft(body.text).to_dict())


# ---------------------------------------------------------------------------
# Phase 3 — Learning loop: targets, research, approval queue
# ---------------------------------------------------------------------------
class TargetIn(BaseModel):
    name: str
    url: str
    kind: str = "competitor"
    notes: str = ""


@app.get("/api/targets")
def targets_list() -> JSONResponse:
    # All targets (paused included) so the dashboard can offer resume
    items = knowledge_targets.list_targets(active_only=False)
    return JSONResponse({"items": items, "hunger": knowledge_targets.hunger_report()})


@app.post("/api/targets")
def targets_add(body: TargetIn) -> JSONResponse:
    try:
        tid = knowledge_targets.add_target(body.name, body.url, body.kind, body.notes)
    except ValueError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)
    return JSONResponse({"target_id": tid}, status_code=201)


@app.post("/api/targets/{target_id}/research")
def targets_research(target_id: int) -> JSONResponse:
    try:
        result = knowledge_targets.research_target(target_id)
    except ValueError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=404)
    return JSONResponse(result, status_code=200 if result.get("ok") else 502)


@app.post("/api/targets/{target_id}/pause")
def targets_pause(target_id: int) -> JSONResponse:
    if not knowledge_targets.pause_target(target_id):
        return JSONResponse({"detail": "target not found"}, status_code=404)
    return JSONResponse({"paused": True, "target_id": target_id})


@app.post("/api/targets/{target_id}/resume")
def targets_resume(target_id: int) -> JSONResponse:
    if not knowledge_targets.resume_target(target_id):
        return JSONResponse({"detail": "target not found"}, status_code=404)
    return JSONResponse({"resumed": True, "target_id": target_id})


@app.get("/api/approvals")
def approvals(limit: int = 100) -> JSONResponse:
    queue = knowledge_targets.approval_queue(limit=limit)
    return JSONResponse({"items": queue, "pending": len(queue)})


# ---------------------------------------------------------------------------
# Phase 4 — Research engine: sweep, watch list, opportunities, briefing
# ---------------------------------------------------------------------------
class WatchIn(BaseModel):
    term: str
    note: str = ""


@app.post("/api/sweep")
def run_sweep() -> JSONResponse:
    """One research pass over all active targets (the scheduler calls this)."""
    return JSONResponse(research_sweep.sweep())


@app.get("/api/briefing")
def briefing(hours: int = 24) -> JSONResponse:
    return JSONResponse(research_briefing.build_briefing(hours=hours))


@app.get("/api/opportunities")
def opportunities(limit: int = 20) -> JSONResponse:
    items = research_opportunities.detect_opportunities()[:limit]
    return JSONResponse({"items": items, "total": len(items)})


@app.get("/api/watchlist")
def watchlist_get() -> JSONResponse:
    return JSONResponse({"items": research_watchlist.list_watch()})


@app.post("/api/watchlist")
def watchlist_add(body: WatchIn) -> JSONResponse:
    try:
        wid = research_watchlist.add_watch(body.term, body.note)
    except ValueError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)
    return JSONResponse({"watch_id": wid}, status_code=201)


@app.post("/api/watchlist/{watch_id}/remove")
def watchlist_remove(watch_id: int) -> JSONResponse:
    if not research_watchlist.remove_watch(watch_id):
        return JSONResponse({"detail": "watch not found"}, status_code=404)
    return JSONResponse({"removed": True, "watch_id": watch_id})


# ---------------------------------------------------------------------------
# Phase 5 — Prospecting: lead finder, pipeline (tiny CRM)
# ---------------------------------------------------------------------------
class LeadIn(BaseModel):
    name: str
    kind: str = "business"
    location: str = ""
    url: str | None = None
    contact: str = ""
    notes: str = ""


class StageIn(BaseModel):
    stage: str
    note: str = ""


@app.get("/api/leads")
def leads_list(stage: str | None = None, min_score: int = 0) -> JSONResponse:
    items = sales_leads.list_leads(stage=stage, min_score=min_score)
    return JSONResponse({"items": items, "total": len(items),
                         "pipeline": sales_pipeline.pipeline_report()})


@app.post("/api/leads/find")
def leads_find(min_score: int = 30) -> JSONResponse:
    """Mine the knowledge base for named businesses worth contacting."""
    return JSONResponse(sales_leads.find_leads(min_score=min_score))


@app.post("/api/leads")
def leads_add(body: LeadIn) -> JSONResponse:
    try:
        lid = sales_leads.add_lead(
            body.name, body.kind, body.location, body.url, body.contact,
            notes=body.notes,
        )
    except ValueError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)
    return JSONResponse(sales_leads.get_lead(lid), status_code=201)


@app.get("/api/leads/{lead_id}")
def lead_get(lead_id: int) -> JSONResponse:
    lead = sales_leads.get_lead(lead_id)
    if not lead:
        return JSONResponse({"detail": "lead not found"}, status_code=404)
    return JSONResponse(lead)


@app.post("/api/leads/{lead_id}/stage")
def lead_stage(lead_id: int, body: StageIn) -> JSONResponse:
    try:
        return JSONResponse(sales_pipeline.move_stage(lead_id, body.stage, body.note))
    except ValueError as exc:
        status = 404 if "not found" in str(exc) else 400
        return JSONResponse({"detail": str(exc)}, status_code=status)


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
