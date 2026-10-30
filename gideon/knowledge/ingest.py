"""Ingest — how Gideon turns pages into knowledge (the hunger mechanism's teeth).

Pipeline: fetch → clean → split into candidate facts → dedupe → store UNAPPROVED.
Approval stays with the owner (constitution gate); ingestion itself is a GREEN
action (`ingest_knowledge_draft`) — Gideon collects, never decides what's kept.

Text extraction is deliberately simple (strip tags/scripts, collapse whitespace):
good enough for facts, zero dependencies. html2text-quality parsing comes later
if a source needs it.
"""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import urljoin

from gideon.brain import hunger
from gideon.knowledge import store

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_TAG_STRIP = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_ANY_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t]+")

MIN_FACT_CHARS = 25    # below this it's navigation crumbs, not knowledge
MAX_FACT_CHARS = 400   # one fact = one idea; long paragraphs get split further

# Category hints: first match wins, checked in order
CATEGORY_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("pricing", ("price", "pricing", "cost", "deposit", "payment", "kes", "quote")),
    ("services", ("service", "build", "design", "website", "seo", "booking", "development",
                  "integration", "landing", "maintenance")),
    ("process", ("process", "discovery", "strategy", "launch", "review", "phase", "step")),
    ("portfolio", ("client", "project", "case study", "built for", "states barbershop",
                   "work", "delivered")),
    ("about", ("founded", "about", "studio", "team", "mission", "kisii", "kenya", "based in")),
    ("contact", ("contact", "whatsapp", "email", "call", "phone", "reach")),
]


def guess_category(text: str) -> str:
    lowered = text.lower()
    for category, hints in CATEGORY_HINTS:
        if any(h in lowered for h in hints):
            return category
    return "general"


def html_to_text(html: str) -> str:
    """Strip scripts/styles/tags → readable whitespace-normalized text."""
    html = _TAG_STRIP.sub(" ", html)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</(p|div|li|h[1-6]|section|article|tr)>", "\n", html, flags=re.IGNORECASE)
    html = _ANY_TAG.sub(" ", html)
    text = unescape(html)
    lines = [_WS.sub(" ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def split_facts(text: str) -> list[str]:
    """Break cleaned text into candidate facts (one idea each)."""
    out: list[str] = []
    for chunk in _SENTENCE_SPLIT.split(text):
        chunk = " ".join(chunk.split())
        if len(chunk) < MIN_FACT_CHARS:
            continue
        if len(chunk) <= MAX_FACT_CHARS:
            out.append(chunk)
        else:
            # Long sentence → split on semicolons/colons, then hard-wrap as last resort
            pieces = re.split(r"(?<=[;:])\s+", chunk)
            for piece in pieces:
                piece = piece.strip()
                if len(piece) < MIN_FACT_CHARS:
                    continue
                if len(piece) <= MAX_FACT_CHARS:
                    out.append(piece)
                else:
                    out.extend(_hard_wrap(piece))
    return out


def _hard_wrap(text: str, width: int = MAX_FACT_CHARS) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        if len(current) + len(word) + 1 > width and current:
            lines.append(current.strip())
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current.strip())
    return [line for line in lines if len(line) >= MIN_FACT_CHARS]


def fetch_page(url: str, *, timeout: float = 20.0) -> str:
    """Fetch a URL and return cleaned text (raises on network failure)."""
    import httpx

    resp = httpx.get(url, timeout=timeout, follow_redirects=True,
                     headers={"User-Agent": "GideonBot/0.1 (Nexora growth agent)"})
    resp.raise_for_status()
    return html_to_text(resp.text)


def ingest_text(
    text: str,
    *,
    source: str | None = None,
    category: str | None = None,
    approved: bool = False,
) -> dict:
    """Turn raw text into candidate facts. Dedupes exact repeats already stored.

    Returns {"added": [...fact_ids], "skipped": int, "chars": int} and records
    a hunger intake event — this is Gideon eating.
    """
    facts = split_facts(text)
    existing = {
        " ".join(f["content"].lower().split())
        for f in store.list_facts(limit=10_000)
    }
    added: list[int] = []
    skipped = 0
    for fact in facts:
        if fact.lower() in existing:
            skipped += 1
            continue
        cat = category or guess_category(fact)
        added.append(store.add_fact(fact, cat, source, approved=approved))
        existing.add(fact.lower())

    if added:
        hunger.record_intake(source or "unknown-source", len(text), kind="ingest")
    return {"added": added, "skipped": skipped, "chars": len(text)}


def ingest_url(url: str, *, approved: bool = False) -> dict:
    """Fetch a page, extract text, ingest it. Records provenance per fact."""
    text = fetch_page(url)
    result = ingest_text(text, source=url, approved=approved)
    result["url"] = url
    return result


def discover_same_site_urls(url: str, html: str, *, limit: int = 20) -> list[str]:
    """Same-origin links found in a page — Phase 2 crawl frontier (no robots
    magic, no external deps: plain href scan)."""
    origin = re.match(r"^(https?://[^/]+)", url)
    if not origin:
        return []
    base = origin.group(1)
    seen: list[str] = []
    for match in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
        link = urljoin(url, unescape(match.group(1)))
        if link.startswith(base) and link not in seen and not re.search(
            r"\.(png|jpg|jpeg|gif|svg|css|js|ico|pdf|zip)$", link, re.IGNORECASE
        ):
            seen.append(link)
        if len(seen) >= limit:
            break
    return seen
