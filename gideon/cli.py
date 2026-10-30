"""Gideon command line: init | doctor | serve."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from gideon import __version__
from gideon.config import DATA_SUBFOLDERS, ROOT, get_settings
from gideon.core import constitution
from gideon.memory import db


def cmd_init(_args: argparse.Namespace) -> int:
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    for sub in DATA_SUBFOLDERS:
        (settings.data_dir / sub).mkdir(exist_ok=True)
        keep = settings.data_dir / sub / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")
    versions = db.init_db()
    applied = ", ".join(f"v{v}" for v in versions) or "already up to date"
    print(f"✓ data dir   : {settings.data_dir}")
    print(f"✓ database   : {settings.db_path}")
    print(f"✓ migrations : {applied}")
    return 0


def _check(label: str, ok: bool, detail: str = "", warn: bool = False) -> bool:
    mark = "✓" if ok else ("!" if warn else "✗")
    line = f"{mark} {label:<22} {detail}".rstrip()
    print(line)
    return ok or warn


def cmd_doctor(_args: argparse.Namespace) -> int:
    print(f"GIDEON doctor — v{__version__}\n")
    all_ok = True

    all_ok &= _check("python", sys.version_info >= (3, 12), sys.version.split()[0])
    all_ok &= _check("project root", ROOT.exists(), str(ROOT))

    settings = get_settings()
    all_ok &= _check(
        "data dir writable",
        _writable(settings.data_dir),
        str(settings.data_dir),
    )
    all_ok &= _check(
        "settings", settings.settings_file.exists(),
        str(settings.settings_file.name),
    )

    const_ok = constitution.load_constitution().get("version") is not None
    all_ok &= _check(
        "constitution", const_ok,
        f"tier={constitution.autonomy_level()}, "
        f"claims={len(constitution.ledger_claims())}",
    )

    probe = db.healthcheck()
    all_ok &= _check(
        "database", bool(probe.get("ok")),
        "tables=" + str(len(probe.get("tables", []))) if probe.get("ok")
        else str(probe.get("error", "")),
    )

    brain_dir = settings.data_dir / "brain"
    has_brain = brain_dir.exists() and any(brain_dir.glob("*.pt"))
    all_ok &= _check(
        "brain (Phase 1)", has_brain,
        "checkpoint found" if has_brain else "not trained yet — Phase 1 builds it",
        warn=True,
    )

    git = shutil.which("git")
    all_ok &= _check("git", bool(git), git or "not found", warn=True)

    node = shutil.which("node")
    npm_modules = ROOT / "web" / "node_modules"
    all_ok &= _check(
        "frontend deps", node and npm_modules.exists(),
        "node + npm packages" if node and npm_modules.exists()
        else "run: cd web && npm install",
        warn=True,
    )

    print("\n" + ("✓ READY — foundation healthy" if all_ok
                  else "✗ FIX THE FAILURES ABOVE"))
    return 0 if all_ok else 1


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def cmd_serve(_args: argparse.Namespace) -> int:
    from gideon.app import run

    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db.init_db()
    print(f"Gideon dashboard → http://127.0.0.1:8420  (data: {settings.data_dir})")
    run(host=_args.host, port=_args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    # Windows consoles default to cp1252 which can't print ✓/✗/→ — force UTF-8
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    parser = argparse.ArgumentParser(prog="gideon", description="GIDEON — Nexora Growth Agent")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create data folders + initialize database").set_defaults(
        func=cmd_init
    )
    sub.add_parser("doctor", help="health check everything").set_defaults(func=cmd_doctor)

    serve = sub.add_parser("serve", help="run the dashboard")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8420)
    serve.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
