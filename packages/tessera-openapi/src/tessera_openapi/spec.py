"""Load an OpenAPI 3.x / Swagger 2.0 spec and iterate its operations."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options", "trace")
_PATH_PARAM_RE = re.compile(r"\{([^}]+)\}")

SPEC_FILENAMES = ("openapi.yaml", "openapi.yml", "openapi.json", "swagger.yaml", "swagger.yml", "swagger.json")


def find_spec_file(input_path: Path) -> Path | None:
    if input_path.is_file():
        return input_path
    for name in SPEC_FILENAMES:
        candidate = input_path / name
        if candidate.exists():
            return candidate
    # fall back to the first yaml/json that looks like a spec
    for p in sorted(input_path.glob("*")):
        if p.suffix.lower() in (".yaml", ".yml", ".json") and _looks_like_spec(p):
            return p
    return None


def _looks_like_spec(path: Path) -> bool:
    try:
        head = path.read_text(encoding="utf-8")[:2000]
    except (OSError, UnicodeDecodeError):
        return False
    return "openapi" in head or "swagger" in head


def load_spec(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text) or {}


def spec_version(doc: dict[str, Any]) -> str:
    if "openapi" in doc:
        return str(doc["openapi"])
    if "swagger" in doc:
        return str(doc["swagger"])
    return ""


def path_params_in(path: str) -> list[str]:
    return _PATH_PARAM_RE.findall(path)


def iter_operations(doc: dict[str, Any]):
    """Yield (path, method, operation_dict, path_level_params)."""
    paths = doc.get("paths", {}) or {}
    for path, item in paths.items():
        if not isinstance(item, dict):
            continue
        shared_params = item.get("parameters", []) or []
        for method, op in item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(op, dict):
                continue
            yield path, method.lower(), op, shared_params
