from __future__ import annotations

import re
from collections import Counter

from tessera_core.models import ValidationFinding

from tessera_prompts.schema import PromptCase

_NAME_RE = re.compile(r"^[a-z0-9]+([_-][a-z0-9]+)*$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+([+-][0-9A-Za-z.-]+)?$")


def validate_prompts(cases: list[PromptCase]) -> list[ValidationFinding]:
    """Per-record and cross-record validation."""
    findings: list[ValidationFinding] = []

    for case in cases:
        findings.extend(_validate_one(case))

    # Cross-record: duplicate name+version pairs
    pair_counts = Counter((c.name, c.version) for c in cases if c.name)
    for (name, version), count in pair_counts.items():
        if count > 1:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="duplicate_name_version",
                    message=f"{count} prompts share name='{name}' version='{version}'",
                    field="name",
                    metadata={"name": name, "version": version, "count": count},
                )
            )

    return findings


def _validate_one(case: PromptCase) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    source = case.metadata.get("source_file", "")

    def f(severity: str, code: str, message: str, field: str | None = None) -> ValidationFinding:
        return ValidationFinding(
            severity=severity,
            code=code,
            message=message,
            field=field,
            metadata={"name": case.name, "source_file": source},
        )

    if not case.name:
        findings.append(f("error", "missing_name", f"{source}: frontmatter has no name field", "name"))
    elif not _NAME_RE.match(case.name):
        findings.append(
            f("warning", "non_canonical_name",
              f"name '{case.name}' is not kebab-case or snake-case", "name")
        )

    if not _SEMVER_RE.match(case.version):
        findings.append(
            f("warning", "invalid_version",
              f"version '{case.version}' is not SemVer (expected X.Y.Z)", "version")
        )

    if not case.description:
        findings.append(f("warning", "missing_description", "description is empty", "description"))
    elif len(case.description) < 10:
        findings.append(
            f("info", "short_description",
              f"description '{case.description}' is shorter than 10 chars", "description")
        )

    if not case.body.strip():
        findings.append(f("error", "empty_body", "prompt body is empty", "body"))

    declared = {v.name for v in case.variables}
    extracted = set(case.extracted_variables)

    for v in sorted(extracted - declared):
        findings.append(
            f("warning", "undeclared_variable",
              f"body uses '{{{{{v}}}}}' but variable '{v}' is not declared", "variables")
        )
    for v in sorted(declared - extracted):
        findings.append(
            f("info", "unused_variable",
              f"variable '{v}' is declared but not used in the body", "variables")
        )

    required_vars = {v.name for v in case.variables if v.required}
    for idx, ex in enumerate(case.examples, start=1):
        supplied = set(ex.input.keys())
        missing = sorted(required_vars - supplied)
        if missing:
            findings.append(
                f("warning", "example_missing_required_variable",
                  f"example #{idx} does not supply required variable(s): {missing}", "examples")
            )

    return findings
