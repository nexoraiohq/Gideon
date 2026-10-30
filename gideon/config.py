"""Single source of truth for paths and settings.

Rules:
- Project root is fixed; everything the agent *learns* lives under DATA_DIR.
- Settings load from config/settings.yaml with GIDEON_* environment overrides.
- Nothing outside DATA_DIR is ever written at runtime.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

# Project root = folder containing the gideon/ package
ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
WEB_DIR = ROOT / "web"
TESTS_DIR = ROOT / "tests"

DEFAULT_DATA_DIR = ROOT / "data"

# Subfolders created by `gideon.cli init`
DATA_SUBFOLDERS = (
    "knowledge",
    "reports",
    "screens",
    "inbox",
    "logs",
    "backups",
)


@dataclass(frozen=True)
class Settings:
    """Resolved runtime settings."""

    data_dir: Path
    raw: dict = field(default_factory=dict)

    # --- key paths -------------------------------------------------------
    @property
    def db_path(self) -> Path:
        return self.data_dir / "gideon.db"

    @property
    def settings_file(self) -> Path:
        return CONFIG_DIR / "settings.yaml"

    @property
    def constitution_file(self) -> Path:
        return CONFIG_DIR / "constitution.yaml"

    @property
    def knowledge_dir(self) -> Path:
        return self.data_dir / "knowledge"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    @property
    def screens_dir(self) -> Path:
        return self.data_dir / "screens"

    @property
    def inbox_dir(self) -> Path:
        return self.data_dir / "inbox"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    # --- convenience getters --------------------------------------------
    def get(self, dotted_key: str, default=None):
        """Fetch a nested setting, e.g. get('research.morning_hour', 7)."""
        node = self.raw
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _resolve_data_dir(raw: dict) -> Path:
    env = os.environ.get("GIDEON_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    configured = raw.get("paths", {}).get("data_dir")
    if configured:
        p = Path(configured)
        return p if p.is_absolute() else (ROOT / p).resolve()
    return DEFAULT_DATA_DIR


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    raw = _load_yaml(CONFIG_DIR / "settings.yaml")
    data_dir = _resolve_data_dir(raw)
    return Settings(data_dir=data_dir, raw=raw)


def reset_settings_cache() -> None:
    """Tests use this after changing environment variables."""
    get_settings.cache_clear()
