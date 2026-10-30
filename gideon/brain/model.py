"""Gideon's cortex — a decoder-only transformer written here, from scratch.

- Random initialization: it is born knowing nothing (no borrowed weights, ever).
- Causal self-attention + MLP blocks, pre-LayerNorm (stable on CPU training).
- `device` comes from config/settings.yaml: "cpu" now, "cuda" the day a GPU exists.
- generate() is the brain's mouth: sample next tokens from context.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class BrainConfig:
    vocab_size: int
    block_size: int = 128       # context length (v0)
    n_embd: int = 192           # ~3M params with vocab ~2k, 4 layers
    n_head: int = 4
    n_layer: int = 4
    dropout: float = 0.1
    device: str = "cpu"


class CausalSelfAttention(nn.Module):
    def __init__(self, cfg: BrainConfig) -> None:
        super().__init__()
        assert cfg.n_embd % cfg.n_head == 0
        self.n_head = cfg.n_head
        self.qkv = nn.Linear(cfg.n_embd, 3 * cfg.n_embd)
        self.proj = nn.Linear(cfg.n_embd, cfg.n_embd)
        self.dropout = nn.Dropout(cfg.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, t, c = x.shape
        q, k, v = self.qkv(x).split(c, dim=2)
        # (B, T, C) -> (B, nh, T, head_dim)
        q = q.view(b, t, self.n_head, c // self.n_head).transpose(1, 2)
        k = k.view(b, t, self.n_head, c // self.n_head).transpose(1, 2)
        v = v.view(b, t, self.n_head, c // self.n_head).transpose(1, 2)
        y = F.scaled_dot_product_attention(
            q, k, v,
            is_causal=True,
            dropout_p=self.dropout.p if self.training else 0.0,
        )
        y = y.transpose(1, 2).contiguous().view(b, t, c)
        return self.dropout(self.proj(y))


class Block(nn.Module):
    def __init__(self, cfg: BrainConfig) -> None:
        super().__init__()
        self.ln1 = nn.LayerNorm(cfg.n_embd)
        self.attn = CausalSelfAttention(cfg)
        self.ln2 = nn.LayerNorm(cfg.n_embd)
        self.mlp = nn.Sequential(
            nn.Linear(cfg.n_embd, 4 * cfg.n_embd),
            nn.GELU(),
            nn.Linear(4 * cfg.n_embd, cfg.n_embd),
            nn.Dropout(cfg.dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln1(x))
        x = x + self.mlp(self.ln2(x))
        return x


class GideonBrain(nn.Module):
    def __init__(self, cfg: BrainConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.tok_emb = nn.Embedding(cfg.vocab_size, cfg.n_embd)
        self.pos_emb = nn.Embedding(cfg.block_size, cfg.n_embd)
        self.drop = nn.Dropout(cfg.dropout)
        self.blocks = nn.ModuleList(Block(cfg) for _ in range(cfg.n_layer))
        self.ln_f = nn.LayerNorm(cfg.n_embd)
        self.lm_head = nn.Linear(cfg.n_embd, cfg.vocab_size, bias=False)
        self.apply(self._init_weights)

    @staticmethod
    def _init_weights(module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    @property
    def num_params(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def forward(
        self, idx: torch.Tensor, targets: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        _, t = idx.shape
        if t > self.cfg.block_size:
            raise ValueError(
                f"sequence {t} exceeds context {self.cfg.block_size}"
            )
        pos = torch.arange(t, device=idx.device)
        x = self.drop(self.tok_emb(idx) + self.pos_emb(pos))
        for block in self.blocks:
            x = block(x)
        logits = self.lm_head(self.ln_f(x))

        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)), targets.view(-1)
            )
        return logits, loss

    @torch.no_grad()
    def generate(
        self,
        idx: torch.Tensor,
        max_new_tokens: int,
        temperature: float = 0.8,
        top_k: int | None = 40,
    ) -> torch.Tensor:
        self.eval()
        for _ in range(max_new_tokens):
            ctx = idx[:, -self.cfg.block_size:]
            logits, _ = self(ctx)
            logits = logits[:, -1, :] / max(temperature, 1e-5)
            if top_k is not None:
                kth = torch.topk(logits, min(top_k, logits.size(-1))).values
                logits[logits < kth[:, [-1]]] = -float("inf")
            probs = F.softmax(logits, dim=-1)
            nxt = torch.multinomial(probs, num_samples=1)
            idx = torch.cat([idx, nxt], dim=1)
        return idx
