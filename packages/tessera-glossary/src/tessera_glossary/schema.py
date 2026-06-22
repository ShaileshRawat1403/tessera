from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Term(BaseModel):
    """A domain vocabulary word. Serialized to ``glossary.jsonl``."""

    term: str
    count: int = 0
    in_code: bool = False
    in_docs: bool = False
    examples: list[str] = Field(default_factory=list)  # sample identifiers/contexts
    metadata: dict[str, Any] = Field(default_factory=dict)
