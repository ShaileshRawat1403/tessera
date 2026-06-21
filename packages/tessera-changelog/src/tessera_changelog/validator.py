from __future__ import annotations

from typing import Any

from tessera_core.models import ValidationFinding

from tessera_changelog.schema import Commit

_WIP_MARKERS = ("wip", "fixup!", "squash!", "tmp", "temp commit")


def validate_changelog_records(commits: list[Commit], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    for err in options.get("_errors", []):
        findings.append(
            ValidationFinding(severity="error", code="source_error",
                              message=err.get("error", "unknown error"), field=None,
                              metadata={"line": err.get("line", "")})
        )

    if not commits and not options.get("_errors"):
        findings.append(ValidationFinding(severity="warning", code="no_commits",
                                          message="no commits found in range", field=None))

    for c in commits:
        ident = c.short_hash or c.hash[:8]

        def f(severity: str, code: str, message: str) -> ValidationFinding:
            return ValidationFinding(severity=severity, code=code, message=message,
                                     field=None, metadata={"hash": ident, "subject": c.subject})

        if not c.subject.strip():
            findings.append(f("warning", "empty_subject", "commit has an empty subject"))
            continue

        if not c.conventional:
            findings.append(f("info", "non_conventional_commit",
                              f"'{c.subject}' is not a Conventional Commit (type: scope: ...)"))

        low = c.subject.lower()
        if any(low.startswith(m) or m in low for m in _WIP_MARKERS):
            findings.append(f("warning", "wip_commit",
                              f"'{c.subject}' looks like a WIP/fixup commit that may not belong in a release"))

        if c.breaking:
            findings.append(f("warning", "breaking_change",
                              f"'{c.subject}' is a BREAKING change"))

    return findings
