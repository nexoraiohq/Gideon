"""GIDEON'S OWN BRAIN — built from scratch. No pretrained weights, ever.

Modules:
- tokenizer: character-level byte-pair encoding, trained on our corpus (pure Python)
- model: decoder-only transformer (needs torch — imported lazily)
- train: curriculum training loop (CPU now, CUDA when a GPU arrives)

Layout mirrors a human mind: see symbols (tokenizer) → sequence patterns (model)
→ grow through practice (train).
"""

from __future__ import annotations

__all__ = ["BPETokenizer"]
from gideon.brain.tokenizer import BPETokenizer  # noqa: E402
