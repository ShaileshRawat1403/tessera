from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tessera_license.detect import category_for, detect_from_text, normalize_declared
from tessera_license.schema import LicenseFinding

_IGNORE = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}
_LICENSE_NAMES = ("license", "licence", "copying", "license.txt", "license.md")

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore


def _is_license_file(name: str) -> bool:
    n = name.lower()
    return n in _LICENSE_NAMES or n.startswith("license") or n.startswith("licence") or n == "copying"


def load_license_records(input_path: Path, options: dict[str, Any]) -> list[LicenseFinding]:
    root = input_path if input_path.is_dir() else input_path.parent
    findings: list[LicenseFinding] = []

    paths = [input_path] if input_path.is_file() else [
        p for p in sorted(root.rglob("*"))
        if p.is_file() and not any(part in _IGNORE for part in p.relative_to(root).parts)
    ]

    for p in paths:
        rel = p.relative_to(root).as_posix() if p.is_relative_to(root) else p.name
        name = p.name.lower()

        if _is_license_file(p.name):
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            lid = detect_from_text(text)
            findings.append(LicenseFinding(source="LICENSE file", path=rel, license_id=lid,
                                           category=category_for(lid), evidence="license file text"))
        elif name == "pyproject.toml":
            _from_pyproject(p, rel, findings)
        elif name == "package.json":
            _from_package_json(p, rel, findings)
        elif name == "cargo.toml":
            _from_cargo(p, rel, findings)

    options["_has_license_file"] = any(f.source == "LICENSE file" for f in findings)
    options["_root"] = str(root)
    return findings


def _record(source: str, rel: str, value: str, findings: list[LicenseFinding]) -> None:
    if not value:
        return
    lid = normalize_declared(value)
    findings.append(LicenseFinding(source=source, path=rel, license_id=lid,
                                   category=category_for(lid), evidence=f"declared: {value}"))


def _from_pyproject(path: Path, rel: str, findings: list[LicenseFinding]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    value = ""
    if tomllib is not None:
        try:
            data = tomllib.loads(text)
            lic = data.get("project", {}).get("license", "")
            if isinstance(lic, dict):
                value = lic.get("text", "") or lic.get("file", "")
            else:
                value = str(lic)
        except Exception:
            value = ""
    if not value:
        m = re.search(r'license\s*=\s*["\']([^"\']+)["\']', text)
        value = m.group(1) if m else ""
    _record("pyproject", rel, value, findings)


def _from_package_json(path: Path, rel: str, findings: list[LicenseFinding]) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return
    lic = data.get("license", "")
    if isinstance(lic, dict):
        lic = lic.get("type", "")
    _record("package.json", rel, str(lic), findings)


def _from_cargo(path: Path, rel: str, findings: list[LicenseFinding]) -> None:
    text = path.read_text(encoding="utf-8")
    value = ""
    if tomllib is not None:
        try:
            value = str(tomllib.loads(text).get("package", {}).get("license", ""))
        except Exception:
            value = ""
    if not value:
        m = re.search(r'license\s*=\s*["\']([^"\']+)["\']', text)
        value = m.group(1) if m else ""
    _record("cargo", rel, value, findings)
