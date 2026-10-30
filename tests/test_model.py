"""Tests for Gideon's cortex — requires torch (Phase 1 dependency)."""

import pytest
import torch

from gideon.brain.model import BrainConfig, GideonBrain

TINY = BrainConfig(
    vocab_size=64, block_size=16, n_embd=32, n_head=2, n_layer=1,
    dropout=0.0, device="cpu",
)


@pytest.fixture(scope="module")
def brain() -> GideonBrain:
    torch.manual_seed(0)
    return GideonBrain(TINY)


def test_forward_shapes(brain):
    idx = torch.randint(0, TINY.vocab_size, (2, 10))
    logits, loss = brain(idx)
    assert logits.shape == (2, 10, TINY.vocab_size)
    assert loss is None


def test_loss_finite_with_targets(brain):
    idx = torch.randint(0, TINY.vocab_size, (2, 8))
    targets = torch.randint(0, TINY.vocab_size, (2, 8))
    _, loss = brain(idx, targets)
    assert loss is not None and torch.isfinite(loss)


def test_causality(brain):
    """Changing a FUTURE token must not alter PAST logits — the mask is real."""
    brain.eval()
    a = torch.randint(0, TINY.vocab_size, (1, 12))
    b = a.clone()
    b[0, -1] = (b[0, -1] + 1) % TINY.vocab_size  # alter only the last token
    with torch.no_grad():
        la, _ = brain(a)
        lb, _ = brain(b)
    assert torch.allclose(la[0, :-1], lb[0, :-1], atol=1e-5)
    assert not torch.allclose(la[0, -1], lb[0, -1], atol=1e-5)


def test_sequence_too_long_raises(brain):
    with pytest.raises(ValueError, match="exceeds context"):
        brain(torch.randint(0, TINY.vocab_size, (1, TINY.block_size + 1)))


def test_generate_extends_sequence(brain):
    idx = torch.randint(0, TINY.vocab_size, (1, 4))
    out = brain.generate(idx, max_new_tokens=5, top_k=10)
    assert out.shape == (1, 9)
    assert int(out.max()) < TINY.vocab_size


def test_overfits_single_sequence():
    """The brain must be able to LEARN: loss drops on memorized data."""
    torch.manual_seed(0)
    model = GideonBrain(TINY)
    model.train()
    seq = torch.randint(0, TINY.vocab_size, (1, 12))
    x, y = seq[:, :-1], seq[:, 1:]
    opt = torch.optim.Adam(model.parameters(), lr=3e-3)

    _, first = model(x, y)
    for _ in range(120):
        _, loss = model(x, y)
        opt.zero_grad()
        loss.backward()
        opt.step()
    _, final = model(x, y)
    assert final.item() < first.item() * 0.7


def test_param_count_reasonable(brain):
    # tiny net: embeddings + 1 block + head — all parameters must be counted
    assert brain.num_params > 10_000
    named = {n for n, _ in brain.named_parameters()}
    assert "tok_emb.weight" in named and "lm_head.weight" in named
