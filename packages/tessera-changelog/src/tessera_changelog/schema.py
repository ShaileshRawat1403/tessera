from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Commit(BaseModel):
    """A canonical commit record. Serialized to ``commits.jsonl``."""

    hash: str = ""
    short_hash: str = ""
    author: str = ""
    date: str = ""
    subject: str = ""
    body: str = ""
    type: str = "other"  # feat / fix / docs / refactor / perf / test / build / ci / chore / style / other
    scope: str = ""
    breaking: bool = False
    conventional: bool = False
    pr_number: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
