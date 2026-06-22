from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LicenseFinding(BaseModel):
    """A detected license declaration. Serialized to ``licenses.jsonl``."""

    source: str          # "LICENSE file" / "pyproject" / "package.json" / "cargo"
    path: str
    license_id: str = "" # detected SPDX-ish id, e.g. MIT / Apache-2.0 / GPL-3.0 / unknown
    category: str = ""   # permissive / copyleft / weak-copyleft / public-domain / unknown
    evidence: str = ""   # how it was detected
    metadata: dict[str, Any] = Field(default_factory=dict)
