from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Dependency(BaseModel):
    """A declared dependency. Serialized to ``dependencies.jsonl``."""

    name: str
    ecosystem: str = ""    # python / npm / cargo / go
    scope: str = "main"    # main / dev / optional / peer
    raw: str = ""          # raw spec as written
    constraint: str = ""   # version constraint portion
    pinning: str = "unpinned"  # pinned / ranged / unpinned
    source_file: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
