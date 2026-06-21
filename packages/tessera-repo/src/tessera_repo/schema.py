from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RepoFile(BaseModel):
    """One inventoried file. Serialized to ``files.jsonl``."""

    path: str  # repo-relative, POSIX
    language: str = "unknown"
    kind: str = "other"  # source / test / config / docs / build / data / asset / other
    loc: int = 0
    bytes: int = 0


class RepoManifest(BaseModel):
    """A detected dependency manifest and the dependencies it declares."""

    kind: str  # pyproject / package_json / requirements / cargo / go_mod
    path: str
    dependencies: list[str] = Field(default_factory=list)


class RepoMap(BaseModel):
    """Aggregate structural map. Serialized to ``repo_map.json``."""

    root: str
    file_count: int = 0
    total_loc: int = 0
    total_bytes: int = 0
    languages: dict[str, int] = Field(default_factory=dict)
    by_kind: dict[str, int] = Field(default_factory=dict)
    top_dirs: dict[str, int] = Field(default_factory=dict)
    manifests: list[RepoManifest] = Field(default_factory=list)
    signals: dict[str, Any] = Field(default_factory=dict)
