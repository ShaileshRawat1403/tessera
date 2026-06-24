from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from tessera_workflow.schema import WorkflowDefinition

_EXTENSIONS = {".workflow.yaml", ".workflow.yml", ".workflow.json"}


def _is_workflow_file(path: Path) -> bool:
    name = path.name.lower()
    return any(name.endswith(ext) for ext in _EXTENSIONS) or (
        path.suffix in {".yaml", ".yml", ".json"} and "workflow" in name
    )


def discover_workflow_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if _is_workflow_file(root) else []
    return sorted(p for p in root.rglob("*") if p.is_file() and _is_workflow_file(p))


def _parse_raw(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    return yaml.safe_load(text) or {}


def load_workflow_records(
    input_path: Path,
    options: dict[str, Any],
) -> list[WorkflowDefinition]:
    files = discover_workflow_files(input_path)
    if not files:
        options["_parse_errors"] = [
            {"file": str(input_path), "error": "no .workflow.yaml / .workflow.json files found"}
        ]
        return []

    records: list[WorkflowDefinition] = []
    errors: list[dict[str, Any]] = []

    for path in files:
        try:
            raw = _parse_raw(path)
        except Exception as exc:
            errors.append({"file": str(path), "error": f"YAML/JSON parse error: {exc}"})
            continue

        try:
            records.append(WorkflowDefinition(**raw))
        except ValidationError as exc:
            for err in exc.errors():
                errors.append({
                    "file": str(path),
                    "error": f"{'.'.join(str(l) for l in err['loc'])}: {err['msg']}",
                })

    options["_parse_errors"] = errors
    options["_source_files"] = [str(f) for f in files]
    return records
