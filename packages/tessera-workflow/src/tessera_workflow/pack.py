from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_core.jobpack import JobPack
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_workflow.compiler import load_records, validate_records, write_artifacts
from tessera_workflow.schema import WorkflowDefinition


class WorkflowPack(JobPack):
    name = "workflow"
    description = "Validate Workflow Pack profile definitions (governance schema, review gates, recursion fence)."

    def normalize(self, input_path: Path, options: dict[str, Any]) -> list[WorkflowDefinition]:
        return load_records(input_path, options)

    def validate(self, records: list[WorkflowDefinition], options: dict[str, Any]) -> list[ValidationFinding]:
        return validate_records(records, options)

    def generate(self, records: list[WorkflowDefinition], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
        return write_artifacts(records, ctx, options)


def create_pack() -> WorkflowPack:
    return WorkflowPack()
