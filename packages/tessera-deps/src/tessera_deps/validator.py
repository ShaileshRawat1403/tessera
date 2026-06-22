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

    # --- lockfile-vs-manifest drift ---
    locks: dict[str, dict[str, str]] = options.get("_locks", {})
    ecosystems_with_deps = {d.ecosystem for d in deps}
    for eco in sorted(ecosystems_with_deps):
        eco_deps = [d for d in deps if d.ecosystem == eco]
        locked = locks.get(eco)
        if locked is None:
            # requirements.txt is itself the pinned source; only flag a missing
            # lock where one is the norm (npm/cargo).
            if eco in ("npm", "cargo"):
                findings.append(
                    ValidationFinding(
                        severity="info", code="lockfile_missing",
                        message=f"{eco} dependencies are declared but no lockfile was found; builds are not reproducible",
                        field="deps", metadata={"ecosystem": eco},
                    )
                )
            continue
        for d in eco_deps:
            if d.name not in locked:
                findings.append(
                    ValidationFinding(
                        severity="warning", code="declared_not_locked",
                        message=f"{d.name} ({eco}) is declared in {d.source_file} but absent from the lockfile; the lock is stale",
                        field="deps", metadata={"name": d.name, "ecosystem": eco, "source_file": d.source_file},
                    )
                )
            elif d.pinning == "pinned" and d.constraint and locked[d.name]:
                pinned_ver = d.constraint.lstrip("=^~ ")
                if pinned_ver and locked[d.name] != pinned_ver:
                    findings.append(
                        ValidationFinding(
                            severity="warning", code="locked_version_mismatch",
                            message=f"{d.name} ({eco}) is pinned to {pinned_ver} but locked at {locked[d.name]}",
                            field="deps", metadata={"name": d.name, "ecosystem": eco,
                                                    "pinned": pinned_ver, "locked": locked[d.name]},
                        )
                    )

    return findings
