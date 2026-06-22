from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tessera_schema.schema import SchemaDoc

_IGNORE_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}
_SKIP_NAMES = {"package.json", "package-lock.json", "tsconfig.json", "composer.json",
               "manifest.json", "babel.config.json", "jsconfig.json", "components.json"}


def _looks_like_schema(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    return any(k in data for k in ("$schema", "properties", "$defs", "definitions")) or \
        (data.get("type") in ("object", "array", "string", "number", "integer", "boolean"))


def discover_schema_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    out: list[Path] = []
    for p in sorted(root.rglob("*.json")):
        if any(part in _IGNORE_DIRS for part in p.relative_to(root).parts):
            continue
        if p.name.lower() in _SKIP_NAMES:
            continue
        out.append(p)
    return out


def load_schema_records(input_path: Path, options: dict[str, Any]) -> list[SchemaDoc]:
    root = input_path if input_path.is_dir() else input_path.parent
    candidates = discover_schema_files(input_path if input_path.is_file() else root)

    docs: list[SchemaDoc] = []
    parse_errors: list[dict[str, str]] = []
    for f in candidates:
        rel = f.relative_to(root).as_posix() if f.is_relative_to(root) else f.name
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            parse_errors.append({"path": rel, "error": str(exc)})
            continue
        if not _looks_like_schema(data):
            continue

        props = data.get("properties", {})
        defs = data.get("$defs", data.get("definitions", {}))
        docs.append(
            SchemaDoc(
                path=rel,
                schema_id=str(data.get("$id", "")),
                schema_version=str(data.get("$schema", "")),
                title=str(data.get("title", "")),
                type=str(data.get("type", "")),
                properties=sorted(props.keys()) if isinstance(props, dict) else [],
                required=[str(r) for r in data.get("required", []) or []],
                defs=sorted(defs.keys()) if isinstance(defs, dict) else [],
                additional_properties_set=("additionalProperties" in data),
            )
        )

    options["_parse_errors"] = parse_errors
    options["_file_count"] = len(docs)
    options["_root"] = str(root)
    return docs
