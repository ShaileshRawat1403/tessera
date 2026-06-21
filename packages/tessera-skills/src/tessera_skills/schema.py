from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

FileKind = Literal["skill", "script", "reference", "example", "data", "other"]


class SkillFile(BaseModel):
    """An inventoried file inside a skill folder."""

    path: str  # relative to the skill root
    kind: FileKind = "other"
    size_bytes: int = 0


class SkillDependencies(BaseModel):
    """Runtime dependencies extracted from SKILL.md body."""

    bash_commands: list[str] = Field(default_factory=list)
    mcp_tools: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class SkillManifest(BaseModel):
    """Canonical skill record. Pack-facing schema; serialized to ``index.jsonl``."""

    name: str
    description: str = ""
    version: str = "0.1.0"
    license: str = ""
    lang: str = "en"
    tags: list[str] = Field(default_factory=list)
    body: str = ""
    files: list[SkillFile] = Field(default_factory=list)
    total_bytes: int = 0
    dependencies: SkillDependencies = Field(default_factory=SkillDependencies)
    metadata: dict[str, Any] = Field(default_factory=dict)
