"""Parse dependency manifests into Dependency records (best-effort, no network)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from tessera_deps.schema import Dependency

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore

_PEP508_NAME = re.compile(r"^([A-Za-z0-9._-]+)")


def _split_name_constraint(spec: str) -> tuple[str, str]:
    spec = spec.strip()
    # drop environment markers and extras
    spec = spec.split(";", 1)[0].strip()
    m = _PEP508_NAME.match(spec)
    if not m:
        return spec, ""
    name = m.group(1)
    constraint = spec[len(name):].strip()
    # strip extras like [security]
    constraint = re.sub(r"^\[[^\]]*\]", "", constraint).strip()
    return name, constraint


def _python_pinning(constraint: str) -> str:
    c = constraint.strip()
    if not c or c == "*":
        return "unpinned"
    if "==" in c:
        return "pinned"
    if any(op in c for op in (">=", "<=", "~=", ">", "<", "!=", "^", "~")):
        return "ranged"
    return "unpinned"


def parse_requirements(path: Path, rel: str) -> list[Dependency]:
    out: list[Dependency] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        name, constraint = _split_name_constraint(line)
        if not name:
            continue
        out.append(Dependency(
            name=name, ecosystem="python", scope="main", raw=line,
            constraint=constraint, pinning=_python_pinning(constraint), source_file=rel,
        ))
    return out


def parse_pyproject(path: Path, rel: str) -> list[Dependency]:
    text = path.read_text(encoding="utf-8")
    out: list[Dependency] = []

    def add(specs, scope):
        for spec in specs or []:
            name, constraint = _split_name_constraint(str(spec))
            if name:
                out.append(Dependency(name=name, ecosystem="python", scope=scope, raw=str(spec),
                                      constraint=constraint, pinning=_python_pinning(constraint), source_file=rel))

    if tomllib is not None:
        data = tomllib.loads(text)
        project = data.get("project", {})
        add(project.get("dependencies", []), "main")
        for _group, specs in (project.get("optional-dependencies", {}) or {}).items():
            add(specs, "optional")
    else:  # regex fallback for main deps (Python 3.10 without tomllib)
        m = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.DOTALL)
        if m:
            specs = [a or b for a, b in re.findall(r'"([^"]+)"|\'([^\']+)\'', m.group(1))]
            add(specs, "main")
    return out


def parse_package_json(path: Path, rel: str) -> list[Dependency]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[Dependency] = []
    scope_map = {"dependencies": "main", "devDependencies": "dev", "peerDependencies": "peer"}
    for key, scope in scope_map.items():
        block = data.get(key, {})
        if not isinstance(block, dict):
            continue
        for name, version in block.items():
            v = str(version)
            if v in ("", "*", "latest"):
                pinning = "unpinned"
            elif re.match(r"^\d", v):
                pinning = "pinned"
            else:
                pinning = "ranged"
            out.append(Dependency(name=name, ecosystem="npm", scope=scope, raw=f"{name}@{v}",
                                  constraint=v, pinning=pinning, source_file=rel))
    return out


def parse_cargo(path: Path, rel: str) -> list[Dependency]:
    text = path.read_text(encoding="utf-8")
    out: list[Dependency] = []
    if tomllib is None:
        return out
    data = tomllib.loads(text)
    for table, scope in (("dependencies", "main"), ("dev-dependencies", "dev")):
        for name, val in (data.get(table, {}) or {}).items():
            version = val if isinstance(val, str) else (val.get("version", "") if isinstance(val, dict) else "")
            v = str(version)
            if not v or v == "*":
                pinning = "unpinned"
            elif v.startswith("="):
                pinning = "pinned"
            else:
                pinning = "ranged"  # cargo bare version means caret range
            out.append(Dependency(name=name, ecosystem="cargo", scope=scope, raw=f"{name} = {v}",
                                  constraint=v, pinning=pinning, source_file=rel))
    return out


def parse_go_mod(path: Path, rel: str) -> list[Dependency]:
    out: list[Dependency] = []
    in_block = False
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("require ("):
            in_block = True
            continue
        if in_block and s == ")":
            in_block = False
            continue
        target = None
        if in_block and s:
            target = s
        elif s.startswith("require ") and "(" not in s:
            target = s[len("require "):].strip()
        if target:
            parts = target.split()
            if len(parts) >= 2:
                # go modules pin exact versions in require
                out.append(Dependency(name=parts[0], ecosystem="go", scope="main", raw=target,
                                      constraint=parts[1], pinning="pinned", source_file=rel))
    return out
