"""Gideon's own byte-pair tokenizer — implemented from scratch.

Design: character-level BPE over raw text.
- Symbols start as single characters; repeated merges learn frequent pairs
  ("th", " the", …) exactly the way BPE was originally described — but written here,
  trained on OUR corpus, no external tokenizer downloads.
- encode → decode round-trips perfectly for any text whose characters were seen
  in training (unknown chars map to <unk>).
- Persisted as JSON in data/brain/tokenizer.json.

Memory notes: training is O(corpus_chars × merges) in the worst case; v0 corpora
are sized (0.5–5 MB) for a 6 GB RAM machine — the corpus pipeline enforces limits.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

UNK = "<unk>"
UNK_ID = 0


class BPETokenizer:
    """Character-level BPE: train on text, encode to ids, decode back."""

    def __init__(self) -> None:
        self.merges: list[tuple[str, str]] = []      # ordered: earlier = higher priority
        self.vocab: dict[str, int] = {UNK: UNK_ID}   # symbol -> id
        self._merge_rank: dict[tuple[str, str], int] = {}

    # ------------------------------------------------------------------ train
    def train(self, text: str, vocab_size: int) -> "BPETokenizer":
        """Learn `vocab_size - len(initial symbols)` merges from `text`.

        vocab_size counts all symbols INCLUDING the <unk> token.
        """
        if not text:
            raise ValueError("cannot train on empty text")
        if vocab_size < 32:
            raise ValueError("vocab_size must be at least 32")

        # Seed vocab with every character present in the corpus
        symbols: list[str] = list(text)
        alphabet = sorted(set(symbols))
        self.vocab = {UNK: UNK_ID}
        for ch in alphabet:
            self.vocab[ch] = len(self.vocab)

        target_merges = vocab_size - len(self.vocab)
        self.merges = []
        for _ in range(max(0, target_merges)):
            pair_counts = Counter(zip(symbols, symbols[1:]))
            if not pair_counts:
                break
            best_pair, best_count = pair_counts.most_common(1)[0]
            if best_count < 2:
                break  # nothing frequent left — vocabulary is saturated
            merged = best_pair[0] + best_pair[1]
            self.merges.append(best_pair)
            self.vocab.setdefault(merged, len(self.vocab))
            symbols = _apply_merge(symbols, best_pair, merged)

        self._reindex()
        return self

    def _reindex(self) -> None:
        self._merge_rank = {pair: i for i, pair in enumerate(self.merges)}

    # ----------------------------------------------------------------- encode
    def encode(self, text: str) -> list[int]:
        ids: list[int] = []
        for symbol in self._bpe(text):
            ids.append(self.vocab.get(symbol, UNK_ID))
        return ids

    def _bpe(self, text: str) -> Iterable[str]:
        # Apply merges in rank order, left-to-right — deterministic and simple.
        symbols = list(text)
        for pair in self.merges:
            symbols = _apply_merge(symbols, pair, pair[0] + pair[1])
        return symbols

    # ----------------------------------------------------------------- decode
    def decode(self, ids: list[int]) -> str:
        reverse = {i: s for s, i in self.vocab.items()}
        parts = [reverse.get(i, "") for i in ids]
        return "".join("" if p == UNK else p for p in parts)

    # ------------------------------------------------------------- persistence
    @property
    def vocab_size(self) -> int:
        return len(self.vocab)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"merges": [list(p) for p in self.merges], "vocab": self.vocab},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "BPETokenizer":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        tok = cls()
        tok.merges = [tuple(p) for p in data["merges"]]
        tok.vocab = {str(k): int(v) for k, v in data["vocab"].items()}
        tok._reindex()
        return tok


def _apply_merge(symbols: list[str], pair: tuple[str, str], merged: str) -> list[str]:
    out: list[str] = []
    i = 0
    n = len(symbols)
    while i < n:
        if i + 1 < n and symbols[i] == pair[0] and symbols[i + 1] == pair[1]:
            out.append(merged)
            i += 2
        else:
            out.append(symbols[i])
            i += 1
    return out
