from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Link(BaseModel):
    """A markdown link. Serialized to ``links.jsonl``."""

    source_file: str
    lineno: int = 0
    text: str = ""
    href: str = ""
    kind: str = "internal"   # internal / anchor / external / mailto
    target_path: str = ""    # resolved repo-relative path for internal links
    anchor: str = ""
    broken: bool = False
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
