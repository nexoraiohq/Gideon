"""Tests for Gideon's own BPE tokenizer — pure Python, no torch needed."""

import pytest

from gideon.brain.tokenizer import UNK, UNK_ID, BPETokenizer

CORPUS = (
    "Nexora Studio builds fast, mobile-first websites for salons and "
    "barbershops in Kisii, Kenya. Booking flows, WhatsApp integration and "
    "SEO foundations built in. The best proof comes from the people who "
    "experienced the work. We build connected systems, not isolated assets. "
    "Strategy, experience, systems and intelligence working together. "
) * 20


def test_train_produces_vocab_and_merges():
    tok = BPETokenizer().train(CORPUS, vocab_size=200)
    assert tok.vocab_size > 32
    assert 0 < len(tok.merges) < 200
    assert tok.vocab[UNK] == UNK_ID


def test_round_trip_perfect():
    tok = BPETokenizer().train(CORPUS, vocab_size=300)
    for sample in (CORPUS[:500], "Kisii, Kenya", "mobile-first websites"):
        assert tok.decode(tok.encode(sample)) == sample


def test_merges_learn_frequent_pairs():
    """'the' and 'ing'-style pairs must show up as merged symbols."""
    tok = BPETokenizer().train(CORPUS, vocab_size=400)
    symbols = set(tok.vocab)
    # at least one multi-char symbol exists (learning happened)
    assert any(len(s) > 1 for s in symbols if s != UNK)
    # common bigrams from the corpus become symbols
    assert any(s in symbols for s in ("th", "the", "he ", "e ", "in", "ng"))


def test_encode_returns_ids():
    tok = BPETokenizer().train(CORPUS, vocab_size=200)
    ids = tok.encode("mobile websites")
    assert all(isinstance(i, int) and i >= UNK_ID for i in ids)
    assert len(ids) <= len("mobile websites")  # merges compress


def test_unknown_chars_map_to_unk_and_decode_cleanly():
    tok = BPETokenizer().train("abcdef", vocab_size=64)
    ids = tok.encode("abc\u2713")  # ✓ never seen in training
    assert UNK_ID in ids
    assert tok.decode(ids) == "abc"  # unknowns vanish, not crash


def test_save_load_identical(tmp_path):
    tok = BPETokenizer().train(CORPUS, vocab_size=250)
    path = tmp_path / "tokenizer.json"
    tok.save(path)
    loaded = BPETokenizer.load(path)
    assert loaded.vocab == tok.vocab
    assert loaded.merges == tok.merges
    assert loaded.encode("Kisii, Kenya") == tok.encode("Kisii, Kenya")


def test_training_is_deterministic():
    a = BPETokenizer().train(CORPUS, vocab_size=150)
    b = BPETokenizer().train(CORPUS, vocab_size=150)
    assert a.merges == b.merges
    assert a.vocab == b.vocab


def test_empty_corpus_rejected():
    with pytest.raises(ValueError):
        BPETokenizer().train("", vocab_size=100)
    with pytest.raises(ValueError):
        BPETokenizer().train("text", vocab_size=10)
