from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

VariableType = Literal["string", "number", "boolean", "list", "object"]


class PromptVariable(BaseModel):
    """A declared variable that appears in the prompt body as ``{{name}}``."""

    name: str
    type: VariableType = "string"
    required: bool = True
    description: str = ""


class PromptExample(BaseModel):
    """An inline example bound to a prompt."""

    input: dict[str, Any] = Field(default_factory=dict)
    expected: str | None = None
    notes: str = ""


class PromptCase(BaseModel):
    """Canonical prompt record. Pack-facing schema; serialized to ``index.jsonl``."""

    name: str
    description: str = ""
    version: str = "0.1.0"
    lang: str = "en"
    tags: list[str] = Field(default_factory=list)
    body: str = ""
    variables: list[PromptVariable] = Field(default_factory=list)
    extracted_variables: list[str] = Field(default_factory=list)
    model_hints: dict[str, Any] = Field(default_factory=dict)
    examples: list[PromptExample] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
