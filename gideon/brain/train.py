"""Curriculum training for Gideon's brain v0 — from random init, on our corpus.

Run:  python -m gideon.brain.train --steps 300
Saves: data/brain/v0.pt (+ tokenizer.json) and logs an audit event.

Design:
- AdamW + grad clipping, train/val split, periodic eval — standard practice,
  implemented here (no trainer libraries).
- device comes from config/settings.yaml (cpu now; `cuda` works the day a GPU exists).
- Sized for a 6 GB machine: corpus capped, activations tiny, batches small.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import asdict
from pathlib import Path

import torch

from gideon.brain.corpus import load_corpus
from gideon.brain.model import BrainConfig, GideonBrain
from gideon.brain.tokenizer import BPETokenizer
from gideon.config import get_settings

BRAIN_DIR_NAME = "brain"
TOKENIZER_NAME = "tokenizer.json"
CHECKPOINT_NAME = "v0.pt"


def brain_paths() -> tuple[Path, Path]:
    base = get_settings().data_dir / BRAIN_DIR_NAME
    return base / TOKENIZER_NAME, base / CHECKPOINT_NAME


def resolve_device(requested: str) -> str:
    if requested.startswith("cuda") and not torch.cuda.is_available():
        print("! cuda requested but not available — falling back to cpu")
        return "cpu"
    return requested


def prepare(
    text: str, tokenizer: BPETokenizer, block_size: int = 128
) -> tuple[torch.Tensor, torch.Tensor]:
    """Encode corpus and split train/val — guard adapts to the REAL corpus size.

    Both sides must hold at least one full context window, or batching would
    silently fail later; we fail fast here with an actionable message instead.
    """
    ids = torch.tensor(tokenizer.encode(text), dtype=torch.long)
    min_side = block_size + 2
    min_total = min_side * 2
    if len(ids) < min_total:
        raise ValueError(
            f"corpus too small: {len(ids)} tokens (need >= {min_total} for "
            f"context {block_size}) — add text to data/corpus/*.txt first"
        )
    split = min(int(len(ids) * 0.9), len(ids) - min_side)
    split = max(split, min_side)
    return ids[:split], ids[split:]


def get_batch(data: torch.Tensor, batch_size: int, block_size: int, device: str):
    starts = torch.randint(0, len(data) - block_size - 1, (batch_size,))
    x = torch.stack([data[s : s + block_size] for s in starts])
    y = torch.stack([data[s + 1 : s + block_size + 1] for s in starts])
    return x.to(device), y.to(device)


@torch.no_grad()
def estimate_loss(
    model: GideonBrain, data: torch.Tensor, batch_size: int, device: str
) -> float:
    was_training = model.training
    model.eval()
    losses = []
    block = model.cfg.block_size
    for _ in range(10):
        x, y = get_batch(data, batch_size, block, device)
        _, loss = model(x, y)
        losses.append(float(loss))
    model.train(was_training)
    return sum(losses) / len(losses)


def train(
    steps: int = 300,
    batch_size: int = 8,
    lr: float = 1e-3,
    eval_every: int = 50,
    log=print,
) -> dict:
    settings = get_settings()
    brain_cfg = settings.get("brain", {}) or {}
    device = resolve_device(str(brain_cfg.get("device", "cpu")))
    tok_path, ckpt_path = brain_paths()

    log("— Gideon brain v0: loading curriculum…")
    corpus = load_corpus()
    if corpus.chars < 500:
        raise ValueError("corpus empty — put .txt files in data/corpus/")

    if tok_path.exists():
        tokenizer = BPETokenizer.load(tok_path)
        log(f"  tokenizer loaded ({tokenizer.vocab_size} symbols)")
    else:
        tokenizer = BPETokenizer().train(corpus.text, vocab_size=2000)
        tokenizer.save(tok_path)
        log(f"  tokenizer trained from scratch ({tokenizer.vocab_size} symbols)")

    cfg = BrainConfig(
        vocab_size=tokenizer.vocab_size,
        block_size=int(brain_cfg.get("v0", {}).get("context_length", 128)),
        n_embd=192, n_head=4, n_layer=4,
        dropout=0.1, device=device,
    )
    train_data, val_data = prepare(corpus.text, tokenizer, cfg.block_size)
    log(f"  corpus: {corpus.chars} chars from {len(corpus.files)} file(s)")
    log(f"  train tokens: {len(train_data):,} | val: {len(val_data):,}")
    model = GideonBrain(cfg).to(device)
    log(f"  model: {model.num_params:,} params (born from random init) on {device}")

    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    model.train()
    t0 = time.time()
    first_loss = last_loss = None

    for step in range(1, steps + 1):
        x, y = get_batch(train_data, batch_size, cfg.block_size, device)
        _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()

        last_loss = loss.item()
        first_loss = first_loss if first_loss is not None else last_loss
        if step % eval_every == 0 or step == steps:
            val = estimate_loss(model, val_data, batch_size, device)
            rate = step / max(time.time() - t0, 1e-6)
            log(
                f"  step {step:>5}/{steps} | train {last_loss:.3f} "
                f"| val {val:.3f} | {rate:.1f} steps/s"
            )

    # A newborn's first words
    prompt = "Nexora "
    p_ids = torch.tensor([tokenizer.encode(prompt)], dtype=torch.long, device=device)
    out = model.generate(p_ids, max_new_tokens=60, temperature=0.8, top_k=40)
    sample = tokenizer.decode(out[0].tolist())

    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": model.state_dict(),
            "config": asdict(cfg),
            "steps": steps,
            "val_loss": estimate_loss(model, val_data, batch_size, device),
            "tokenizer": str(tok_path),
        },
        ckpt_path,
    )
    stats = {
        "params": model.num_params,
        "first_loss": first_loss,
        "last_loss": last_loss,
        "steps": steps,
        "sample": sample,
        "checkpoint": str(ckpt_path),
    }
    log(f"  saved → {ckpt_path}")
    log(f"  loss {first_loss:.3f} → {last_loss:.3f}")
    log(f'  the newborn said: "{sample.strip()}"')
    return stats


def main(argv: list[str] | None = None) -> int:
    for stream in (__import__("sys").stdout,):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(description="Train Gideon brain v0")
    p.add_argument("--steps", type=int, default=300)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--lr", type=float, default=1e-3)
    args = p.parse_args(argv)

    try:
        train(steps=args.steps, batch_size=args.batch_size, lr=args.lr)
    except ValueError as exc:
        print(f"✗ {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
