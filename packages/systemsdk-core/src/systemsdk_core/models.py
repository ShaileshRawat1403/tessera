from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RunContext:
    job_name: str
    output_dir: Path
    run_id: str = dc_field(default_factory=lambda: uuid4().hex[:12])
    created_at: datetime = dc_field(default_factory=_utcnow)
    metadata: dict[str, Any] = dc_field(default_factory=dict)


@dataclass
class Artifact:
    name: str
    path: Path
    kind: str
    metadata: dict[str, Any] = dc_field(default_factory=dict)


@dataclass
class ValidationFinding:
    severity: str
    code: str
    message: str
    field: str | None = None
    metadata: dict[str, Any] = dc_field(default_factory=dict)
