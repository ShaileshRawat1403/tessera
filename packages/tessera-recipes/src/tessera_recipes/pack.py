from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_core.jobpack import JobPack
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_recipes.compiler import (
    load_recipe_records,
    validate_recipe_records,
    write_recipe_artifacts,
)


class RecipesPack(JobPack):
    name = "recipes"
    version = "0.3.1"

    def normalize(self, input_path: Path, options: dict[str, Any]) -> list[Any]:
        return load_recipe_records(input_path, options)

    def validate(
        self,
        records: list[Any],
        options: dict[str, Any],
    ) -> list[ValidationFinding]:
        return validate_recipe_records(records, options)

    def generate(
        self,
        records: list[Any],
        ctx: RunContext,
        options: dict[str, Any],
    ) -> list[Artifact]:
        return write_recipe_artifacts(records, ctx, options)


def create_pack() -> RecipesPack:
    return RecipesPack()
