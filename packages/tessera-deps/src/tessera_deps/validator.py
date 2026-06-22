from __future__ import annotations

from collections import defaultdict
from typing import Any

from tessera_core.models import ValidationFinding

from tessera_deps.schema import Dependency


def validate_deps_records(deps: list[Dependency], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    if not deps:
        findings.append(ValidationFinding(severity="info", code="no_dependencies",
                                          message="no dependency manifests found", field=None))
        return findings

    for d in deps:
        if d.pinning == "unpinned":
            findings.append(
                ValidationFinding(
                    severity="warning", code="unpinned_dependency",
                    message=f"{d.name} ({d.source_file}) has no version constraint",
                    field="deps", metadata={"name": d.name, "source_file": d.source_file, "ecosystem": d.ecosystem},
                )
            )

    # duplicates across manifests (same name + ecosystem in more than one file)
    by_key: dict[tuple[str, str], list[Dependency]] = defaultdict(list)
    for d in deps:
        by_key[(d.ecosystem, d.name)].append(d)
    for (eco, name), group in by_key.items():
        files = {d.source_file for d in group}
        if len(files) > 1:
            constraints = {d.constraint for d in group}
            if len(constraints) > 1:
                findings.append(
                    ValidationFinding(
                        severity="warning", code="conflicting_constraint",
                        message=f"{name} ({eco}) declared with differing constraints across {len(files)} files: {sorted(constraints)}",
                        field="deps", metadata={"name": name, "files": sorted(files)},
                    )
                )
            else:
                findings.append(
                    ValidationFinding(
                        severity="info", code="duplicate_dependency",
                        message=f"{name} ({eco}) declared in {len(files)} files",
                        field="deps", metadata={"name": name, "files": sorted(files)},
                    )
                )

    return findings
