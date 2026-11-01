"""Research engine — Gideon's daily rhythm (Phase 4).

- watchlist: subjects Gideon tracks across everything it studies
- sweep: the morning pass — all active targets studied, new facts queued
- opportunities: pattern detector over what Gideon knows (gap → actionable lead)
- briefing: the CEO report — what Gideon did, found, and needs decided

Everything here is local computation over approved + pending facts. The brain's
own scoring replaces keyword heuristics as it grows.
"""

from __future__ import annotations

__all__ = ["watch", "detect_opportunities", "build_briefing"]

# NOTE: `sweep` is deliberately NOT re-exported — the function would shadow the
# gideon.research.sweep *module*. Import it as: from gideon.research import sweep
from gideon.research.watchlist import watch  # noqa: E402,F401
from gideon.research.opportunities import detect_opportunities  # noqa: E402,F401
from gideon.research.briefing import build_briefing  # noqa: E402,F401
