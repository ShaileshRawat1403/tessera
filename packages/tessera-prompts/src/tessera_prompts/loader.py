from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from tessera_prompts.schema import PromptCase, PromptExample, PromptVariable

_VARIABLE_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


def discover_prompt_files(root: Path) -> list[Path]:
    """Find prompt entries under ``root``.

    Two shapes are recognized:
      - file:   ``<name>.prompt.md``
      - folder: ``<name>/PROMPT.md`` (case-insensitive on the basename)
    """
    if root.is_file():
        return [root]

    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name.endswith(".prompt.md"):
            found.append(path)
        elif path.is_file() and path.name.lower() == "prompt.md":
            found.append(path)
    return found


def parse_prompt_file(path: Path) -> PromptCase:
    """Parse a single prompt file into a PromptCase.

    Raises ``ValueError`` when the file has no parseable frontmatter.
    """
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(f"{path}: no YAML frontmatter found")

    raw_meta = yaml.safe_load(m.group(1)) or {}
    body = m.group(2).strip()

    if not isinstance(raw_meta, dict):
        raise ValueError(f"{path}: frontmatter is not a mapping")

    variables = [_coerce_variable(v) for v in raw_meta.get("variables", []) or []]
    examples = [_coerce_example(e) for e in raw_meta.get("examples", []) or []]
    extracted = sorted({m.group(1) for m in _VARIABLE_RE.finditer(body)})

    return PromptCase(
        name=str(raw_meta.get("name", "")),
        description=str(raw_meta.get("description", "")),
        version=str(raw_meta.get("version", "0.1.0")),
        lang=str(raw_meta.get("lang", "en")),
        tags=list(raw_meta.get("tags", []) or []),
        body=body,
        variables=variables,
        extracted_variables=extracted,
        model_hints=dict(raw_meta.get("model_hints", {}) or {}),
        examples=examples,
        metadata={
            "source_file": str(path),
            "source_form": "directory" if path.name.lower() == "prompt.md" else "file",
        },
    )


def _coerce_variable(raw: Any) -> PromptVariable:
    if isinstance(raw, str):
        return PromptVariable(name=raw)
    if isinstance(raw, dict):
        return PromptVariable(
            name=str(raw.get("name", "")),
            type=raw.get("type", "string"),
            required=bool(raw.get("required", True)),
            description=str(raw.get("description", "")),
        )
    return PromptVariable(name=str(raw))


def _coerce_example(raw: Any) -> PromptExample:
    if not isinstance(raw, dict):
        return PromptExample(input={}, expected=str(raw) if raw is not None else None)
    return PromptExample(
        input=dict(raw.get("input", {}) or {}),
        expected=(str(raw["expected"]) if raw.get("expected") is not None else None),
        notes=str(raw.get("notes", "")),
    )
