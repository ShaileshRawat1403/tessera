from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from tessera_core.models import Artifact, RunContext, ValidationFinding


class JobPack(ABC):
    name: str
    version: str = "0.1.0"

    @abstractmethod
    def normalize(self, input_path: Path, options: dict[str, Any]) -> list[Any]:
        """Convert raw input into internal records."""

    @abstractmethod
    def validate(
        self,
        records: list[Any],
        options: dict[str, Any],
    ) -> list[ValidationFinding]:
        """Return data quality findings before generation."""

    @abstractmethod
    def generate(
        self,
        records: list[Any],
        ctx: RunContext,
        options: dict[str, Any],
    ) -> list[Artifact]:
        """Generate final artifacts."""

    def run(
        self,
        input_path: Path,
        ctx: RunContext,
        options: dict[str, Any] | None = None,
    ) -> list[Artifact]:
        options = options or {}
        records = self.normalize(input_path, options)
        findings = self.validate(records, options)
        artifacts = self.generate(records, ctx, options)

        ctx.metadata["record_count"] = len(records)
        ctx.metadata["finding_count"] = len(findings)
        ctx.metadata["findings"] = findings

        return artifacts
