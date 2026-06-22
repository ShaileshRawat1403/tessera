from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_core.jobpack import JobPack
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_skills.compiler import (
    load_skill_records,
    validate_skill_records,
    write_skill_artifacts,
)


class SkillsPack(JobPack):
    name = "skills"
    version = "0.3.1"

    def normalize(self, input_path: Path, options: dict[str, Any]) -> list[Any]:
        return load_skill_records(input_path, options)

    def validate(
        self,
        records: list[Any],
        options: dict[str, Any],
    ) -> list[ValidationFinding]:
        return validate_skill_records(records, options)

    def generate(
        self,
        records: list[Any],
        ctx: RunContext,
        options: dict[str, Any],
    ) -> list[Artifact]:
        return write_skill_artifacts(records, ctx, options)


def create_pack() -> SkillsPack:
    return SkillsPack()
