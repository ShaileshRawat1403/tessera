from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class EvalRecord(BaseModel):
    id: str
    task_type: str
    input: dict[str, Any]
    context: dict[str, Any] = Field(default_factory=dict)
    expected: dict[str, Any] = Field(default_factory=dict)
    rubric: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompileOptions(BaseModel):
    task_type: str
    input_column: str | None = None
    expected_column: str | None = None
    context_column: str | None = None
    golden_mode: Literal["extract", "candidate", "rubric"] = "candidate"
