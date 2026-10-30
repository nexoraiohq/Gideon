"""Corpus pipeline tests — curriculum loading respects caps and sources."""

from gideon.brain.corpus import (
    DEFAULT_MAX_CHARS,
    load_corpus,
    write_seed_corpus,
)


def test_missing_dir_returns_empty_report(tmp_path):
    report = load_corpus(tmp_path / "nope")
    assert report.text == ""
    assert report.files == []
    assert report.chars == 0


def test_loads_all_txt_sorted(tmp_path):
    write_seed_corpus(tmp_path, "b_second.txt", "bravo")
    write_seed_corpus(tmp_path, "a_first.txt", "alpha")
    report = load_corpus(tmp_path)
    assert report.files == ["a_first.txt", "b_second.txt"]
    assert "alpha" in report.text and "bravo" in report.text
    assert report.chars == len(report.text)


def test_cap_enforced_and_flagged(tmp_path):
    write_seed_corpus(tmp_path, "big.txt", "x" * 5000)
    report = load_corpus(tmp_path, max_chars=1000)
    assert report.chars <= 1000
    assert report.truncated is True


def test_normalization_and_strip(tmp_path):
    write_seed_corpus(tmp_path, "n.txt", "a\r\nb   c\r\n\r\n\r\n\r\nd")
    report = load_corpus(tmp_path)
    assert "  " not in report.text
    assert "\r" not in report.text
    assert report.text.endswith("d")


def test_default_cap_is_safe_for_6gb():
    assert DEFAULT_MAX_CHARS <= 2_000_000


def test_seed_writes_into_real_corpus_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("GIDEON_DATA_DIR", str(tmp_path))
    from gideon.config import reset_settings_cache

    reset_settings_cache()
    try:
        path = write_seed_corpus(
            tmp_path / "corpus", "nexora.txt", "Nexora builds websites."
        )
        assert path.exists()
        report = load_corpus()
        assert "Nexora builds websites." in report.text
    finally:
        monkeypatch.delenv("GIDEON_DATA_DIR")
        reset_settings_cache()
