"""Sales — prospecting brain (Phase 5).

- leads: repository over the leads table (find/score/store)
- scoring: how well a lead fits Nexora's Delivery Ledger (explainable, local)
- pipeline: the tiny CRM — stages from discovered to won/lost

No fake promises anywhere: a lead's score ALWAYS comes with the reasons that
produced it, so the owner can judge the recommendation, not trust it blindly.
"""

from __future__ import annotations

__all__ = ["add_lead", "find_leads", "score_lead", "move_stage"]

from gideon.sales.leads import add_lead, find_leads  # noqa: E402,F401
from gideon.sales.scoring import score_lead  # noqa: E402,F401
from gideon.sales.pipeline import move_stage  # noqa: E402,F401
