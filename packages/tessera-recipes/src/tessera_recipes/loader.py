from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from tessera_recipes.schema import Recipe, RecipeIO, RecipeStep

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


def discover_recipe_files(root: Path) -> list[Path]:
    """Find recipe entries under ``root``.

    Two shapes are recognized:
      - file:   ``<name>.recipe.md``
      - folder: ``<name>/RECIPE.md`` (case-insensitive on the basename)
    """
    if root.is_file():
        return [root]

    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name.endswith(".recipe.md"):
            found.append(path)
        elif path.is_file() and path.name.lower() == "recipe.md":
            found.append(path)
    return found


def parse_recipe_file(path: Path) -> Recipe:
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(f"{path}: no YAML frontmatter found")

    raw = yaml.safe_load(m.group(1)) or {}
    body = m.group(2).strip()
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: frontmatter is not a mapping")

    return Recipe(
        name=str(raw.get("name", "") or path.stem.replace(".recipe", "")),
        description=str(raw.get("description", "") or ""),
        version=str(raw.get("version", "0.1.0")),
        lang=str(raw.get("lang", "en")),
        tags=list(raw.get("tags", []) or []),
        inputs=[_coerce_io(i) for i in raw.get("inputs", []) or []],
        outputs=[_coerce_io(o) for o in raw.get("outputs", []) or []],
        steps=[_coerce_step(s) for s in raw.get("steps", []) or []],
        body=body,
        metadata={
            "source_file": str(path),
            "source_form": "directory" if path.name.lower() == "recipe.md" else "file",
        },
    )


def _coerce_io(raw: Any) -> RecipeIO:
    if isinstance(raw, str):
        return RecipeIO(name=raw)
    if isinstance(raw, dict):
        return RecipeIO(
            name=str(raw.get("name", "")),
            type=str(raw.get("type", "string")),
            required=bool(raw.get("required", True)),
            description=str(raw.get("description", "")),
        )
    return RecipeIO(name=str(raw))


def _coerce_step(raw: Any) -> RecipeStep:
    if isinstance(raw, str):
        return RecipeStep(id=raw)
    if not isinstance(raw, dict):
        return RecipeStep(id=str(raw))
    needs = raw.get("needs", []) or []
    if isinstance(needs, str):
        needs = [needs]
    return RecipeStep(
        id=str(raw.get("id", "")),
        uses=str(raw.get("uses", "")),
        description=str(raw.get("description", "")),
        needs=[str(n) for n in needs],
        inputs=dict(raw.get("inputs", {}) or {}),
        produces=str(raw.get("produces", "")),
    )
