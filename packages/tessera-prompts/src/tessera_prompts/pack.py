from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_core.jobpack import JobPack
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_prompts.compiler import (
    load_prompt_records,
    validate_prompt_records,
    write_prompt_artifacts,
)


class PromptsPack(JobPack):
    name = "prompts"
    version = "0.3.0"

    def normalize(self, input_path: Path, options: dict[str, Any]) -> list[Any]:
        return load_prompt_records(input_path, options)

    def validate(
        self,
        records: list[Any],
        options: dict[str, Any],
    ) -> list[ValidationFinding]:
        return validate_prompt_records(records, options)

    def generate(
        self,
        records: list[Any],
        ctx: RunContext,
        options: dict[str, Any],
    ) -> list[Artifact]:
        return write_prompt_artifacts(records, ctx, options)


def create_pack() -> PromptsPack:
    return PromptsPack()
