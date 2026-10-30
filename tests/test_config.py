"""Config tests — settings load, env overrides, path resolution."""

from gideon.config import (
    CONFIG_DIR,
    DATA_SUBFOLDERS,
    ROOT,
    get_settings,
    reset_settings_cache,
)


def test_project_layout():
    assert (ROOT / "gideon").is_dir()
    assert (ROOT / "config").is_dir()
    assert (ROOT / "web").is_dir()
    assert (ROOT / "tests").is_dir()


def test_settings_load():
    s = get_settings()
    assert s.get("dashboard.port") == 8420
    assert s.get("outreach.email_max_per_day") == 20
    assert s.get("research.respect_robots") is True


def test_default_paths():
    s = get_settings()
    assert s.db_path.name == "gideon.db"
    assert s.data_dir.name == "data"
    # every storage subfolder has a resolved property
    for sub in DATA_SUBFOLDERS:
        folder = getattr(s, f"{sub}_dir")
        assert folder.parent == s.data_dir


def test_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("GIDEON_DATA_DIR", str(tmp_path))
    reset_settings_cache()
    try:
        assert get_settings().data_dir == tmp_path.resolve()
    finally:
        monkeypatch.delenv("GIDEON_DATA_DIR")
        reset_settings_cache()


def test_config_dir_versioned_location():
    assert CONFIG_DIR == ROOT / "config"
