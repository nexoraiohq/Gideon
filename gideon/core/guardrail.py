"""Promise guardrail — the "no fake promises" rule, enforced in code.

Every outbound draft (email, WhatsApp, post, proposal) passes through
check_draft() BEFORE the owner sees it:

- GREEN   → the draft's promise-shaped sentences are backed by Delivery Ledger
            claims; safe to send as written.
- YELLOW  → contains promises with no ledger backing; owner sees exactly which
            sentences are risky and why.
- RED     → touches a constitution red-line (contract, refund, legal claim,
            "guarantee" language); blocked outright — it never reaches send.

The guardrail never rewrites text itself (that's drafting's job); it judges and
explains, and the decision tier routes the result.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from gideon.core import constitution
from gideon.knowledge import store

# Hard blocks — red regardless of ledger
RED_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("guarantee language", re.compile(r"\b(guarantee|guaranteed|100%|bulletproof)\b",
                                      re.IGNORECASE)),
    ("legal claim", re.compile(r"\b(sue|legally|legally binding|attorney|contract sign)\b",
                               re.IGNORECASE)),
    ("refund promise", re.compile(r"\b(refund|money[- ]back)\b", re.IGNORECASE)),
    ("price commitment beyond ledger", re.compile(r"\b(free of charge|no payment|won't cost)\b",
                                                  re.IGNORECASE)),
]

# Soft signals — yellow unless ledger-backed
PROMISE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("ranking promise", re.compile(r"\b(first page|page one|top of google|rank #?1|"
                                   r"number one on google)\b", re.IGNORECASE)),
    ("outcome promise", re.compile(r"\b(increase|double|triple|boost).{0,30}\b"
                                   r"(sales|revenue|customers|traffic|bookings)\b",
                                   re.IGNORECASE)),
    ("timeline promise", re.compile(r"\bin (?:just )?\d+ ?(?:days|weeks)\b", re.IGNORECASE)),
    ("scale claim", re.compile(r"\b(hundreds of|thousands of|best-selling|award-winning)\b",
                               re.IGNORECASE)),
]

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class DraftCheck:
    verdict: str                       # green | yellow | red
    red_flags: list[dict] = field(default_factory=list)
    yellow_flags: list[dict] = field(default_factory=list)
    backed_claims: list[str] = field(default_factory=list)

    @property
    def ok_to_send(self) -> bool:
        return self.verdict == "green"

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "ok_to_send": self.ok_to_send,
            "red_flags": self.red_flags,
            "yellow_flags": self.yellow_flags,
            "backed_claims": self.backed_claims,
            "message": _explain(self),
        }


def _ledger_texts() -> list[str]:
    out = []
    for entry in constitution.ledger_claims():
        text = str(entry.get("claim", "")) if isinstance(entry, dict) else str(entry)
        out.append(" ".join(text.lower().split()))
    return out


def _is_ledger_backed(sentence: str) -> str | None:
    """Return the matching ledger claim if this sentence maps to one."""
    norm = " ".join(sentence.lower().split())
    for claim in _ledger_texts():
        # Substring containment: a sentence that IS (or IS contained in) a claim
        # is trivially backed.
        if norm and (claim in norm or norm in claim):
            return claim
        # Backing by content-word overlap: >= 3 shared words means the sentence
        # describes something the ledger actually says.
        claim_words = set(store.tokenize(claim))
        sent_words = set(store.tokenize(sentence))
        if sent_words and len(claim_words & sent_words) >= 3:
            return claim
    return None


def check_draft(text: str) -> DraftCheck:
    """Judge a draft. Never raises on weird input — it's a safety net."""
    text = " ".join((text or "").split())
    result = DraftCheck(verdict="green")
    if not text:
        return result

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]

    for sentence in sentences:
        # Red lines block immediately
        red_hit = None
        for label, pattern in RED_PATTERNS:
            if pattern.search(sentence):
                red_hit = label
                break
        if red_hit:
            result.red_flags.append({"sentence": sentence, "rule": red_hit})
            continue

        # Promise shapes need backing
        for label, pattern in PROMISE_PATTERNS:
            if pattern.search(sentence):
                matched_claim = _is_ledger_backed(sentence)
                if matched_claim:
                    result.backed_claims.append(matched_claim)
                else:
                    result.yellow_flags.append({"sentence": sentence, "rule": label})
                break

    if result.red_flags:
        result.verdict = "red"
    elif result.yellow_flags:
        result.verdict = "yellow"
    return result


def _explain(check: DraftCheck) -> str:
    if check.verdict == "red":
        rules = ", ".join(sorted({f["rule"] for f in check.red_flags}))
        return (f"BLOCKED — red-line violation ({rules}). "
                f"This promise is beyond what Nexora can back; it never gets sent.")
    if check.verdict == "yellow":
        rules = ", ".join(sorted({f["rule"] for f in check.yellow_flags}))
        return (f"Needs your review — {rules}. These claims aren't in the Delivery "
                f"Ledger yet; approve evidence first or reword.")
    if check.backed_claims:
        return "Clean — promises map to Delivery Ledger claims."
    return "Clean — no promise-shaped claims found."
