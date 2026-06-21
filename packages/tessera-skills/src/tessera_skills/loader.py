from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from tessera_skills.deps import (
    extract_bash_commands,
    extract_mcp_tools,
    extract_skill_refs,
)
from tessera_skills.schema import (
    SkillDependencies,
    SkillFile,
    SkillManifest,
)

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


def discover_skill_folders(root: Path) -> list[Path]:
    """Find directories that contain a SKILL.md (case-insensitive on basename)."""
    if root.is_file() and root.name.lower() == "skill.md":
        return [root.parent]

    found: list[Path] = []
    for skill_md in sorted(root.rglob("SKILL.md")):
        if skill_md.is_file():
            found.append(skill_md.parent)
    return found


def parse_skill_folder(folder: Path) -> SkillManifest:
    skill_md = _locate_skill_md(folder)
    if skill_md is None:
        raise ValueError(f"{folder}: no SKILL.md found")

    text = skill_md.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(f"{skill_md}: no YAML frontmatter found")

    raw_meta = yaml.safe_load(m.group(1)) or {}
    body = m.group(2).strip()
    if not isinstance(raw_meta, dict):
        raise ValueError(f"{skill_md}: frontmatter is not a mapping")

    name = str(raw_meta.get("name", "") or folder.name)
    files = _inventory(folder)
    total_bytes = sum(f.size_bytes for f in files)
    deps = SkillDependencies(
        bash_commands=extract_bash_commands(body),
        mcp_tools=extract_mcp_tools(body),
        skills=extract_skill_refs(body, own_name=name),
    )

    return SkillManifest(
        name=name,
        description=str(raw_meta.get("description", "") or ""),
        version=str(raw_meta.get("version", "0.1.0")),
        license=str(raw_meta.get("license", "") or ""),
        lang=str(raw_meta.get("lang", "en")),
        tags=list(raw_meta.get("tags", []) or []),
        body=body,
        files=files,
        total_bytes=total_bytes,
        dependencies=deps,
        metadata={
            "source_folder": str(folder),
            "skill_md_path": str(skill_md.relative_to(folder)),
        },
    )


def _locate_skill_md(folder: Path) -> Path | None:
    for child in folder.iterdir():
        if child.is_file() and child.name.lower() == "skill.md":
            return child
    return None


def _inventory(folder: Path) -> list[SkillFile]:
    files: list[SkillFile] = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(folder)
        files.append(
            SkillFile(
                path=str(rel),
                kind=_classify(rel),
                size_bytes=path.stat().st_size,
            )
        )
    return files


def _classify(rel: Path) -> str:
    name_lower = rel.name.lower()
    if name_lower == "skill.md":
        return "skill"
    parts = {p.lower() for p in rel.parts[:-1]}
    if "scripts" in parts or rel.suffix in {".py", ".sh", ".bash", ".zsh", ".js", ".ts"}:
        return "script"
    if "references" in parts or "docs" in parts:
        return "reference"
    if "examples" in parts or "samples" in parts:
        return "example"
    if rel.suffix in {".json", ".csv", ".tsv", ".yaml", ".yml", ".jsonl"}:
        return "data"
    return "other"
