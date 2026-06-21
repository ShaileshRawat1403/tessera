from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AuthKind = Literal["bearer", "basic", "api_key_header", "api_key_query", "none"]
BodyKind = Literal["json", "form", "text", "none"]


class Redaction(BaseModel):
    """A record of one secret that was removed before canonicalization.

    ``preview`` holds a masked hint only (never the full secret), so the
    redactions report is safe to commit and review.
    """

    location: str  # e.g. "header:authorization", "query:api_key", "body"
    kind: str  # e.g. "bearer_token", "basic_credentials", "api_key"
    preview: str  # e.g. "sk-ab…(redacted, len=51)"


class ApiAuth(BaseModel):
    kind: AuthKind = "none"
    location: str = ""  # e.g. "header:Authorization", "query:api_key"
    present: bool = False


class ApiRequest(BaseModel):
    """Canonical, secret-free API request record. Serialized to ``index.jsonl``."""

    id: str
    method: str = "GET"
    url: str = ""  # redacted form (query secrets masked)
    scheme: str = ""
    host: str = ""
    path: str = ""
    query: dict[str, str] = Field(default_factory=dict)  # redacted values
    headers: dict[str, str] = Field(default_factory=dict)  # redacted values
    body: str | None = None  # redacted
    body_kind: BodyKind = "none"
    auth: ApiAuth = Field(default_factory=ApiAuth)
    redactions: list[Redaction] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
