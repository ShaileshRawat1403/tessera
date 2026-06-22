from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_core.jobpack import JobPack
from tessera_core.models import Artifact, RunContext, ValidationFinding


class ExamplePack(JobPack):
    name = "example"
    version = "0.3.1"

    def normalize(self, input_path: Path, options: dict[str, Any]) -> list[Any]:
        return [{"input_path": str(input_path)}]

    def validate(
        self,
        records: list[Any],
        options: dict[str, Any],
    ) -> list[ValidationFinding]:
        return []

    def generate(
        self,
        records: list[Any],
        ctx: RunContext,
        options: dict[str, Any],
    ) -> list[Artifact]:
        ctx.output_dir.mkdir(parents=True, exist_ok=True)
        output = ctx.output_dir / "example.txt"
        output.write_text("Example pack executed.\n", encoding="utf-8")
        return [Artifact(name="example.txt", path=output, kind="text")]


def create_pack() -> ExamplePack:
    return ExamplePack()
