"""Answer — retrieval over approved facts, always with citations.

Behavior (Gideon's voice rules):
- Answer ONLY from approved knowledge. No fact → say so plainly; never invent.
- Every answer carries sources — the owner can verify in one glance.
- Ledger check: an answer must not promise beyond the Delivery Ledger; if the
  retrieved facts would support an unbacked promise, the answer is flagged
  yellow for owner review instead of being returned as clean.
"""

from __future__ import annotations

import re
from typing import Any

from gideon.core import constitution
from gideon.knowledge import store

CONFIDENT_THRESHOLD = 0.5   # >= half the question's words matched a fact
THIN_THRESHOLD = 0.25       # below this we're guessing — say so


def _score_overlap(query: str, content: str) -> float:
    q = set(store.tokenize(query))
    c = set(store.tokenize(content))
    return len(q & c) / len(q) if q else 0.0


# Promise-shaped phrases that require ledger backing before Gideon may say them
PROMISE_PATTERNS = re.compile(
    r"\b(guarantee|guaranteed|we promise|best in|number one|top-rated|"
    r"always rank|first page of google|results?\b.{0,20}\b(days|weeks)|"
    r"roi|revenue increase|increase your .{0,20}by \d+%)",
    re.IGNORECASE,
)


def contains_unbacked_promise(text: str) -> bool:
    """True when copy makes a promise shape that needs ledger/experience backing."""
    if not PROMISE_PATTERNS.search(text):
        return False
    # A promise phrase backed by a ledger claim is allowed (e.g. delivery timelines
    # documented in the FAQ). Backing = a ledger claim shares >=3 content words.
    words = set(store.tokenize(text))
    for claim in constitution.ledger_claims():
        claim_text = str(claim.get("claim", "")) if isinstance(claim, dict) else str(claim)
        if len(words & set(store.tokenize(claim_text))) >= 3:
            return False
    return True


def answer(question: str, *, approved_only: bool = True, limit: int = 4) -> dict[str, Any]:
    """Answer from knowledge. Returns answer + citations + confidence + flags."""
    question = " ".join(question.split())
    if not question:
        raise ValueError("question cannot be empty")

    facts = store.search_facts(question, approved_only=approved_only, limit=limit)
    scored = [
        (f, _score_overlap(question, f["content"])) for f in facts
    ]
    scored = [(f, s) for f, s in scored if s >= THIN_THRESHOLD]

    if not scored:
        msg = (
            "I don't have that in my knowledge yet. I'll research it — "
            "anything I learn stays a draft until you approve it."
        )
        return {
            "question": question,
            "answer": msg,
            "citations": [],
            "confidence": 0.0,
            "needs_research": True,
            "promise_flagged": False,
        }

    best = max(s for _, s in scored)
    lines = [f["content"] for f, _ in scored]
    citations = [
        {"fact_id": f["id"], "content": f["content"], "source_url": f["source_url"],
         "category": f["category"]}
        for f, _ in scored
    ]
    body = " ".join(lines)
    flagged = contains_unbacked_promise(body)

    if best >= CONFIDENT_THRESHOLD:
        opener = "Based on what I've learned:"
    else:
        opener = "What I have so far suggests:"

    return {
        "question": question,
        "answer": f"{opener} {body}",
        "citations": citations,
        "confidence": round(best, 2),
        "needs_research": False,
        "promise_flagged": flagged,
    }
