from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LocaleFile(BaseModel):
    """A locale's coverage relative to the reference. Serialized to ``locales.jsonl``."""

    locale: str
    path: str
    is_reference: bool = False
    key_count: int = 0
    coverage: float = 1.0
    missing_keys: list[str] = Field(default_factory=list)
    extra_keys: list[str] = Field(default_factory=list)
    empty_keys: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
