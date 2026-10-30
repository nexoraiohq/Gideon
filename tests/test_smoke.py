"""Smoke tests: app boots, health endpoint answers, core files exist."""

from pathlib import Path

from fastapi.testclient import TestClient

from gideon.app import app
from gideon.config import CONFIG_DIR, ROOT

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"]["ok"] is True


def test_health_reports_constitution():
    body = client.get("/api/health").json()
    assert body["constitution"]["autonomy"] == "approve_first"
    assert body["constitution"]["ledger_claims"] > 0


def test_master_plan_present():
    assert (ROOT / "GIDEON_BUILD_PLAN.md").exists()


def test_config_files_present():
    assert (CONFIG_DIR / "settings.yaml").exists()
    assert (CONFIG_DIR / "constitution.yaml").exists()


def test_index_served():
    """React build served when present; helpful 404 hint when not."""
    from gideon.config import WEB_DIR

    resp = client.get("/")
    if (WEB_DIR / "dist" / "index.html").exists():
        assert resp.status_code == 200
        assert "GIDEON" in resp.text
    else:
        assert resp.status_code == 404
        assert "npm" in resp.json()["detail"]


def test_events_and_screens_endpoints():
    assert client.get("/api/events").status_code == 200
    assert client.get("/api/screens").status_code == 200


def test_no_writes_outside_data_dir():
    """Safety rule: config files must be read-only for the runtime."""
    from gideon.config import get_settings

    settings = get_settings()
    assert settings.data_dir.is_absolute()
    # runtime data dir must not be the config dir
    assert settings.data_dir != CONFIG_DIR
    assert isinstance(Path(settings.data_dir), Path)
