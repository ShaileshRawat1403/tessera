"""Best-effort dependency-manifest detection and parsing.

Parsing is intentionally lightweight and never executes anything. Declared
dependencies are informational; a manifest that cannot be parsed yields an
empty dependency list rather than an error.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tessera_repo.schema import RepoManifest

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - 3.10 fallback
    tomllib = None  # type: ignore


def detect_and_parse(repo_root: Path, rel_path: Path) -> RepoManifest | None:
    name = rel_path.name.lower()
    full = repo_root / rel_path
    try:
        if name == "pyproject.toml":
            return RepoManifest(kind="pyproject", path=rel_path.as_posix(), dependencies=_parse_pyproject(full))
        if name == "package.json":
            return RepoManifest(kind="package_json", path=rel_path.as_posix(), dependencies=_parse_package_json(full))
        if name == "requirements.txt":
            return RepoManifest(kind="requirements", path=rel_path.as_posix(), dependencies=_parse_requirements(full))
        if name == "cargo.toml":
            return RepoManifest(kind="cargo", path=rel_path.as_posix(), dependencies=_parse_cargo(full))
        if name == "go.mod":
            return RepoManifest(kind="go_mod", path=rel_path.as_posix(), dependencies=_parse_go_mod(full))
    except Exception:
        return RepoManifest(kind=name, path=rel_path.as_posix(), dependencies=[])
    return None


def _dep_name(spec: str) -> str:
    return re.split(r"[<>=!~;\[ ]", spec.strip(), maxsplit=1)[0].strip().strip('"').strip("'")


def _parse_pyproject(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if tomllib is not None:
        data = tomllib.loads(text)
        deps = data.get("project", {}).get("dependencies", []) or []
        return [_dep_name(d) for d in deps if _dep_name(d)]
    # 3.10 fallback: regex the dependencies array
    m = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.DOTALL)
    if not m:
        return []
    items = re.findall(r'"([^"]+)"|\'([^\']+)\'', m.group(1))
    return [_dep_name(a or b) for a, b in items if _dep_name(a or b)]


def _parse_package_json(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        block = data.get(key, {})
        if isinstance(block, dict):
            names.extend(block.keys())
    return sorted(set(names))


def _parse_requirements(path: Path) -> list[str]:
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        name = _dep_name(line)
        if name:
            out.append(name)
    return out


def _parse_cargo(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if tomllib is not None:
        data = tomllib.loads(text)
        return sorted(data.get("dependencies", {}).keys())
    # fallback: lines under [dependencies]
    out: list[str] = []
    in_block = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            in_block = s.lower().startswith("[dependencies")
            continue
        if in_block and "=" in s:
            out.append(s.split("=", 1)[0].strip())
    return out


def _parse_go_mod(path: Path) -> list[str]:
    out: list[str] = []
    in_block = False
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("require ("):
            in_block = True
            continue
        if in_block and s == ")":
            in_block = False
            continue
        if in_block and s:
            out.append(s.split()[0])
        elif s.startswith("require ") and "(" not in s:
            parts = s.split()
            if len(parts) >= 2:
                out.append(parts[1])
    return out
