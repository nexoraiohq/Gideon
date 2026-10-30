"""LLM interface.

Design rule: no module may talk to a model directly — everything goes through
this interface, so we can switch Ollama ↔ cloud API without touching features.

Phase 1 wires the real client; for now availability detection only.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Protocol

OLLAMA_URL = "http://127.0.0.1:11434"


class LLMClient(Protocol):
    """What every module may assume exists."""

    def available(self) -> bool: ...

    def complete(self, prompt: str, system: str = "") -> str: ...


def ollama_status(timeout: float = 1.0) -> dict[str, Any]:
    """Probe the local Ollama server without failing hard if absent."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        models = [m.get("name") for m in data.get("models", [])]
        return {"ok": True, "url": OLLAMA_URL, "models": models}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"ok": False, "url": OLLAMA_URL, "error": str(exc)}


class PlaceholderClient:
    """Deterministic stand-in used until the Ollama client lands in Phase 1."""

    def available(self) -> bool:
        return False

    def complete(self, prompt: str, system: str = "") -> str:
        raise RuntimeError(
            "LLM not wired yet (Phase 1). Install Ollama: https://ollama.com"
        )


def get_client() -> LLMClient:
    return PlaceholderClient()
