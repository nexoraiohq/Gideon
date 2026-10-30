"""Knowledge — what Gideon has learned (with sources, always).

- store: facts table repository (add/approve/search); approval gates long-term memory
- ingest: turning pages/text into candidate facts (hunger feeds on this)
- answer: retrieval over approved facts, with citations — never invented sources

Everything here is local computation (token-overlap retrieval); the brain's own
embeddings replace the scorer in a later phase — no external embedding APIs, ever.
"""

from __future__ import annotations

__all__ = ["add_fact", "approve_fact", "search_facts", "ingest_text"]

# NOTE: `answer` is deliberately NOT re-exported here — doing so shadows the
# gideon.knowledge.answer *module* (import it as: from gideon.knowledge import answer)
from gideon.knowledge.store import add_fact, approve_fact, search_facts  # noqa: E402,F401
from gideon.knowledge.ingest import ingest_text  # noqa: E402,F401
