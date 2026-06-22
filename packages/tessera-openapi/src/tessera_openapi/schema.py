from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Endpoint(BaseModel):
    """One operation from an OpenAPI/Swagger spec. Serialized to ``endpoints.jsonl``."""

    method: str
    path: str
    operation_id: str = ""
    summary: str = ""
    tags: list[str] = Field(default_factory=list)
    path_params: list[str] = Field(default_factory=list)       # {name} in the path template
    declared_path_params: list[str] = Field(default_factory=list)  # parameters with in=path
    has_request_body: bool = False
    responses: list[str] = Field(default_factory=list)
    deprecated: bool = False
    secured: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class SpecInfo(BaseModel):
    """Top-level spec metadata."""

    title: str = ""
    version: str = ""
    spec_version: str = ""   # e.g. "3.0.3" or "2.0"
    server_count: int = 0
    endpoint_count: int = 0
