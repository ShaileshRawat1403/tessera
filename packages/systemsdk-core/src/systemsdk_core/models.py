from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class RunContext(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    job_name: str
    output_dir: Path
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class QualityFinding(BaseModel):
    level: Literal["info", "warning", "error"]
    code: str
    message: str
    record_id: str | None = None


class Artifact(BaseModel):
    name: str
    path: Path
    kind: str
