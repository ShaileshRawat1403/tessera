from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_core.jobpack import JobPack
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_tests.compiler import load_records, validate_records, write_artifacts


class TestsPack(JobPack):
    name = "tests"
    version = "0.2.0"

    def normalize(self, input_path: Path, options: dict[str, Any]) -> list[Any]:
        return load_records(input_path, options)

    def validate(
        self,
        records: list[Any],
        options: dict[str, Any],
    ) -> list[ValidationFinding]:
        return validate_records(records, options)

    def generate(
        self,
        records: list[Any],
        ctx: RunContext,
        options: dict[str, Any],
    ) -> list[Artifact]:
        return write_artifacts(records, ctx, options)


def create_pack() -> TestsPack:
    return TestsPack()
