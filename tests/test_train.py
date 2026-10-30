"""Tests for the training loop — adaptive guards, device fallback, tiny smoke run."""

import pytest
import torch

from gideon.brain.model import BrainConfig, GideonBrain
from gideon.brain.tokenizer import BPETokenizer
from gideon.brain.train import estimate_loss, prepare, resolve_device


def _text(n: int = 200) -> str:
    """Varied text — BPE can't collapse repeats into a handful of mega-symbols."""
    words = ["nexora", "builds", "websites", "in", "kisii", "kenya",
             "design", "booking", "flows", "seo", "fast", "mobile", "first"]
    return " ".join(f"{words[i % len(words)]}{i % 7}" for i in range(n * 8)) + " "


def _tok():
    return BPETokenizer().train(_text(), vocab_size=120)


def test_resolve_device_falls_back_without_cuda():
    assert resolve_device("cpu") == "cpu"
    if not torch.cuda.is_available():
        assert resolve_device("cuda") == "cpu"
        assert resolve_device("cuda:0") == "cpu"


def test_prepare_rejects_tiny_corpus():
    with pytest.raises(ValueError, match="corpus too small"):
        prepare("tiny text", _tok(), block_size=128)


def test_prepare_guarantees_windows_on_both_sides():
    tok = _tok()
    text = _text()
    train_ids, val_ids = prepare(text, tok, block_size=16)
    assert len(train_ids) >= 18 and len(val_ids) >= 18
    assert len(train_ids) + len(val_ids) == len(tok.encode(text))


def test_prepare_is_deterministic():
    text = _text(50)
    tok = _tok()
    a_train, a_val = prepare(text, tok, block_size=16)
    b_train, b_val = prepare(text, tok, block_size=16)
    assert torch.equal(a_train, b_train) and torch.equal(a_val, b_val)


def test_estimate_loss_restores_train_mode():
    torch.manual_seed(0)
    cfg = BrainConfig(vocab_size=32, block_size=8, n_embd=16, n_head=2,
                      n_layer=1, dropout=0.0, device="cpu")
    model = GideonBrain(cfg)
    model.train()
    data = torch.randint(0, 32, (200,))
    loss = estimate_loss(model, data, batch_size=4, device="cpu")
    assert isinstance(loss, float) and loss > 0
    assert model.training is True  # mode restored after eval


def test_estimate_loss_is_no_grad():
    torch.manual_seed(0)
    cfg = BrainConfig(vocab_size=32, block_size=8, n_embd=16, n_head=2,
                      n_layer=1, dropout=0.0, device="cpu")
    model = GideonBrain(cfg)
    data = torch.randint(0, 32, (200,))
    assert estimate_loss(model, data, batch_size=4, device="cpu") >= 0
    assert all(p.grad is None for p in model.parameters())
