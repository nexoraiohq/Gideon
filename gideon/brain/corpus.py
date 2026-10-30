"""Corpus pipeline — what Gideon's brain reads during training.

Rules:
- Sources are ONLY: plain-text files the owner places in data/corpus/, plus text
  Gideon itself captured and the owner approved (data/knowledge/approved/).
  No scraped junk, no other AI's outputs — the curriculum is chosen, like a school.
- Hard size cap keeps the 6 GB machine safe.
- Pure Python, no torch — testable anywhere.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from gideon.config import get_settings

DEFAULT_MAX_CHARS = 1_500_000  # v0 cap: ~1.5 MB of text trains on CPU in reasonable time
SEPARATOR = "\n\n"


@dataclass(frozen=True)
class CorpusReport:
    text: str
    files: list[str]
    chars: int
    truncated: bool

    @property
    def words(self) -> int:
        return len(self.text.split())


def default_corpus_dir() -> Path:
    return get_settings().data_dir / "corpus"


def write_seed_corpus(corpus_dir: Path, name: str, text: str) -> Path:
    """Owner adds/keeps curriculum files. Seeds the directory if empty."""
    corpus_dir.mkdir(parents=True, exist_ok=True)
    path = corpus_dir / name
    path.write_text(_normalize(text), encoding="utf-8")
    return path


def load_corpus(
    corpus_dir: Path | None = None, max_chars: int = DEFAULT_MAX_CHARS
) -> CorpusReport:
    """Read every *.txt in the corpus dir, concatenated, capped at max_chars."""
    corpus_dir = corpus_dir or default_corpus_dir()
    if not corpus_dir.exists():
        return CorpusReport(text="", files=[], chars=0, truncated=False)

    chunks: list[str] = []
    files: list[str] = []
    total = 0
    truncated = False

    for path in sorted(corpus_dir.glob("*.txt")):
        content = _normalize(path.read_text(encoding="utf-8", errors="ignore"))
        if not content:
            continue
        room = max_chars - total
        if room <= 0:
            truncated = True
            break
        if len(content) > room:
            content = content[:room]
            truncated = True
        chunks.append(content)
        files.append(path.name)
        total += len(content)
        if truncated:
            break

    text = SEPARATOR.join(chunks)
    return CorpusReport(text=text, files=files, chars=len(text), truncated=truncated)


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
