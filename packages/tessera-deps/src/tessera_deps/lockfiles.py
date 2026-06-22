"""Parse lockfiles to detect drift against declared manifests (no network)."""

from __future__ import annotations

import json
import re
from pathlib import Path

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore

# lockfile filename -> ecosystem
LOCKFILES = {
    "package-lock.json": "npm",
    "npm-shrinkwrap.json": "npm",
    "yarn.lock": "npm",
    "poetry.lock": "python",
    "cargo.lock": "cargo",
}


def parse_lockfile(path: Path) -> dict[str, str]:
    """Return {package_name: locked_version} for a lockfile, best-effort."""
    name = path.name.lower()
    try:
        if name in ("package-lock.json", "npm-shrinkwrap.json"):
            return _parse_npm_lock(path)
        if name == "yarn.lock":
            return _parse_yarn_lock(path)
        if name == "poetry.lock":
            return _parse_poetry_lock(path)
        if name == "cargo.lock":
            return _parse_cargo_lock(path)
    except Exception:
        return {}
    return {}


def _parse_npm_lock(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    # lockfile v2/v3: "packages": {"node_modules/<name>": {"version": ...}}
    for key, meta in (data.get("packages", {}) or {}).items():
        if not key or not isinstance(meta, dict):
            continue
        pkg = key.split("node_modules/")[-1]
        if pkg:
            out[pkg] = str(meta.get("version", ""))
    # lockfile v1: "dependencies": {<name>: {"version": ...}}
    for pkg, meta in (data.get("dependencies", {}) or {}).items():
        if isinstance(meta, dict):
            out.setdefault(pkg, str(meta.get("version", "")))
    return out


def _parse_yarn_lock(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    current: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith(" ") and line.rstrip().endswith(":"):
            # header like:  "left-pad@^1.0.0", left-pad@^1.1.0:
            current = re.findall(r'"?([^@"\s,]+)@', line)
        elif "version" in line:
            m = re.search(r'version\s+"?([^"\s]+)"?', line)
            if m and current:
                for pkg in current:
                    out.setdefault(pkg, m.group(1))
                current = []
    return out


def _parse_poetry_lock(path: Path) -> dict[str, str]:
    if tomllib is None:
        return {}
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return {str(p.get("name", "")): str(p.get("version", "")) for p in data.get("package", []) if p.get("name")}


def _parse_cargo_lock(path: Path) -> dict[str, str]:
    if tomllib is None:
        return {}
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return {str(p.get("name", "")): str(p.get("version", "")) for p in data.get("package", []) if p.get("name")}
