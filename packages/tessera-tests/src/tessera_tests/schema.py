from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TestCase(BaseModel):
    """A discovered test. Serialized to ``tests.jsonl``."""

    # Tell pytest not to collect this domain model as a test class.
    __test__ = False

    name: str
    qualname: str = ""
    kind: str = "function"   # function / method
    file: str = ""
    lineno: int = 0
    decorators: list[str] = Field(default_factory=list)
    is_skipped: bool = False
    is_xfail: bool = False
    is_parametrized: bool = False
    assertion_count: int = 0
    has_assert: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
