from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_deps.lockfiles import LOCKFILES, parse_lockfile
from tessera_deps.parsers import (
    parse_cargo,
    parse_go_mod,
    parse_package_json,
    parse_pyproject,
    parse_requirements,
)
from tessera_deps.schema import Dependency

_IGNORE = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    "dist", "build", ".tox", "target",
}


def _dispatch(path: Path, rel: str) -> list[Dependency]:
    name = path.name.lower()
    try:
        if name == "pyproject.toml":
            return parse_pyproject(path, rel)
        if name == "package.json":
            return parse_package_json(path, rel)
        if name == "cargo.toml":
            return parse_cargo(path, rel)
        if name == "go.mod":
            return parse_go_mod(path, rel)
        if name == "requirements.txt" or (name.startswith("requirements") and name.endswith(".txt")):
            return parse_requirements(path, rel)
    except Exception:
        return []
    return []


def load_deps_records(input_path: Path, options: dict[str, Any]) -> list[Dependency]:
    root = input_path if input_path.is_dir() else input_path.parent
    manifests: list[str] = []
    deps: list[Dependency] = []

    if input_path.is_file():
        deps.extend(_dispatch(input_path, input_path.name))
        if deps or _dispatch(input_path, input_path.name):
            manifests.append(input_path.name)
    locks: dict[str, dict[str, str]] = {}
    lock_files: list[str] = []
    if not input_path.is_file():
        for p in sorted(root.rglob("*")):
            if any(part in _IGNORE for part in p.relative_to(root).parts):
                continue
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            parsed = _dispatch(p, rel)
            if parsed:
                deps.extend(parsed)
                manifests.append(rel)
            eco = LOCKFILES.get(p.name.lower())
            if eco:
                locked = parse_lockfile(p)
                if locked:
                    locks.setdefault(eco, {}).update(locked)
                    lock_files.append(rel)

    options["_manifests"] = manifests
    options["_locks"] = locks
    options["_lock_files"] = lock_files
    options["_root"] = str(root)
    return deps
