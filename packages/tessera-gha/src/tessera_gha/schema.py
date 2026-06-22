from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkflowItem(BaseModel):
    """A step within a workflow job. Serialized to ``items.jsonl``."""

    workflow: str
    job: str
    step: str = ""
    kind: str = "run"        # "uses" or "run"
    action: str = ""         # action ref for uses, e.g. actions/checkout@v4
    action_pinned: bool = False  # pinned to a 40-char commit SHA
    run_injection: bool = False  # run: script interpolates an untrusted event field
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowInfo(BaseModel):
    """Workflow-level facts. Serialized to ``workflows.jsonl``."""

    workflow: str
    triggers: list[str] = Field(default_factory=list)
    jobs: list[str] = Field(default_factory=list)
    has_top_permissions: bool = False
    jobs_without_permissions: list[str] = Field(default_factory=list)
    jobs_without_timeout: list[str] = Field(default_factory=list)
