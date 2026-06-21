from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvalRecord(BaseModel):
    """Canonical eval record. Pack-facing schema, used for disk artifacts and inter-pack handoff."""

    id: str
    task_type: str
    input: dict[str, Any]
    context: dict[str, Any] = Field(default_factory=dict)
    expected: dict[str, Any] = Field(default_factory=dict)
    rubric: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
