from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkflowStep(BaseModel):
    name: str
    adapter: str
    description: str = ""
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    timeout_s: int = 300


class ReviewGate(BaseModel):
    after_step: str
    label: str = "human_review"
    conditions: list[str] = Field(default_factory=list)


class EvidencePolicy(BaseModel):
    required_artifacts: list[str] = Field(default_factory=list)
    # Steps whose output hash must be identical at promotion to prevent TOCTOU.
    hash_invariant_steps: list[str] = Field(default_factory=list)


class CapabilityEnvelope(BaseModel):
    step: str
    allowed_write_paths: list[str] = Field(default_factory=list)
    denied_write_paths: list[str] = Field(default_factory=list)


class RecursionFence(BaseModel):
    protected_paths: list[str]


class WorkflowDefinition(BaseModel):
    """Workflow Pack profile: a JobPack profile that describes a governed multi-step workflow."""

    name: str
    version: str
    description: str = ""
    steps: list[WorkflowStep]
    required_adapters: list[str] = Field(default_factory=list)
    review_gates: list[ReviewGate] = Field(default_factory=list)
    evidence_policy: EvidencePolicy = Field(default_factory=EvidencePolicy)
    capability_envelopes: list[CapabilityEnvelope] = Field(default_factory=list)
    recursion_fence: RecursionFence | None = None
    # "after_review" | "manual" | "auto"
    promotion_rule: str = "after_review"
    run_state_mapping: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
