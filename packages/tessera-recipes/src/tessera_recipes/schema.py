from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RecipeIO(BaseModel):
    """A declared recipe-level input or output."""

    name: str
    type: str = "string"
    required: bool = True
    description: str = ""


class RecipeStep(BaseModel):
    """A single step in a recipe workflow.

    ``needs`` lists step ids this step depends on explicitly. References of the
    form ``${steps.X}`` inside ``inputs`` are additionally inferred as edges by
    the graph engine, so authors can rely on either or both.
    """

    id: str
    uses: str = ""  # tool / skill / action identifier (free-form in v0.1)
    description: str = ""
    needs: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    produces: str = ""  # name of the output this step yields, if any


class Recipe(BaseModel):
    """Canonical recipe record. Pack-facing schema; serialized to ``index.jsonl``."""

    name: str
    description: str = ""
    version: str = "0.1.0"
    lang: str = "en"
    tags: list[str] = Field(default_factory=list)
    inputs: list[RecipeIO] = Field(default_factory=list)
    outputs: list[RecipeIO] = Field(default_factory=list)
    steps: list[RecipeStep] = Field(default_factory=list)
    body: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
