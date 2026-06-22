from __future__ import annotations

from typing import Any

from tessera_core.models import ValidationFinding

from tessera_tests.schema import TestCase


def validate_test_records(cases: list[TestCase], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    for err in options.get("_parse_errors", []):
        findings.append(ValidationFinding(severity="error", code="parse_error",
                                          message=f"could not parse: {err}", field=None))

    if not cases:
        if not options.get("_parse_errors"):
            findings.append(ValidationFinding(severity="info", code="no_tests_found",
                                              message="no test functions discovered", field=None))
        return findings

    for c in cases:
        loc = f"{c.file}:{c.lineno}"

        def f(severity: str, code: str, message: str) -> ValidationFinding:
            return ValidationFinding(severity=severity, code=code, message=message,
                                     field="tests", metadata={"file": c.file, "lineno": c.lineno, "name": c.qualname})

        if not c.has_assert and not c.is_skipped and not c.is_xfail:
            findings.append(f("warning", "no_assertion_test",
                              f"{loc}: test `{c.qualname}` has no assertions"))
        if c.is_skipped:
            findings.append(f("info", "skipped_test", f"{loc}: test `{c.qualname}` is skipped"))
        if c.is_xfail:
            findings.append(f("info", "xfail_test", f"{loc}: test `{c.qualname}` is expected to fail"))

    return findings
