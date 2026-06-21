from __future__ import annotations

from typing import Any

from tessera_core.models import ValidationFinding

from tessera_repo.schema import RepoFile

LARGE_FILE_LOC = 800


def validate_repo_records(files: list[RepoFile], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    signals: dict = options.get("_signals", {})
    manifests = options.get("_manifests", [])

    if not files:
        findings.append(
            ValidationFinding(severity="error", code="empty_repo",
                              message="no files found (after ignoring build/vendor dirs)", field=None)
        )
        return findings

    if not signals.get("has_readme"):
        findings.append(ValidationFinding(severity="warning", code="missing_readme",
                                          message="no README found at any level", field="docs"))
    if not signals.get("has_license"):
        findings.append(ValidationFinding(severity="info", code="missing_license",
                                          message="no LICENSE file found", field="docs"))
    if not signals.get("has_tests"):
        findings.append(ValidationFinding(severity="warning", code="no_tests_detected",
                                          message="no test files detected", field="tests"))
    if not manifests:
        findings.append(ValidationFinding(severity="info", code="no_dependency_manifest",
                                          message="no dependency manifest found (pyproject/package.json/...)", field="build"))
    if not signals.get("has_ci"):
        findings.append(ValidationFinding(severity="info", code="no_ci_config",
                                          message="no CI config detected (.github/workflows, etc.)", field="build"))

    for f in files:
        if f.loc and f.loc > LARGE_FILE_LOC:
            findings.append(
                ValidationFinding(severity="info", code="large_source_file",
                                  message=f"{f.path} has {f.loc} lines of code (> {LARGE_FILE_LOC})",
                                  field="source", metadata={"path": f.path, "loc": f.loc})
            )

    return findings
