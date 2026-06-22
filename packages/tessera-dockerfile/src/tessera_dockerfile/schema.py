from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Instruction(BaseModel):
    """One Dockerfile instruction. Serialized to ``instructions.jsonl``."""

    instruction: str    # FROM / RUN / COPY / ADD / ENV / USER / ...
    argument: str = ""
    file: str = ""
    lineno: int = 0
    stage: str = ""     # build-stage name when FROM ... AS <stage>
    metadata: dict[str, Any] = Field(default_factory=dict)
