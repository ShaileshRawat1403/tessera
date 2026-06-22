from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SchemaDoc(BaseModel):
    """A JSON Schema document. Serialized to ``schemas.jsonl``."""

    path: str
    schema_id: str = ""
    schema_version: str = ""   # the $schema dialect URI
    title: str = ""
    type: str = ""
    properties: list[str] = Field(default_factory=list)
    required: list[str] = Field(default_factory=list)
    defs: list[str] = Field(default_factory=list)
    additional_properties_set: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
