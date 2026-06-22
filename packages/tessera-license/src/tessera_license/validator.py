from __future__ import annotations

from typing import Any

from tessera_core.models import ValidationFinding

from tessera_license.schema import LicenseFinding


def validate_license_records(records: list[LicenseFinding], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    if not records:
        findings.append(ValidationFinding(severity="warning", code="no_license",
                                          message="no LICENSE file or declared license found", field="license"))
        return findings

    if not options.get("_has_license_file"):
        findings.append(ValidationFinding(severity="warning", code="missing_license_file",
                                          message="a license is declared in a manifest but there is no LICENSE file", field="license"))

    for r in records:
        def f(severity: str, code: str, message: str) -> ValidationFinding:
            return ValidationFinding(severity=severity, code=code, message=message,
                                     field="license", metadata={"source": r.source, "path": r.path, "license": r.license_id})

        if r.category == "copyleft":
            f_ = f("warning", "copyleft_license",
                   f"{r.path}: {r.license_id} is copyleft; review obligations before distribution")
            findings.append(f_)
        if r.license_id == "unknown":
            findings.append(f("info", "unrecognized_license",
                              f"{r.path}: could not identify the license ({r.evidence})"))

    # mismatch across declared licenses
    ids = {r.license_id for r in records if r.license_id != "unknown"}
    if len(ids) > 1:
        findings.append(ValidationFinding(severity="warning", code="license_mismatch",
                                          message=f"multiple different licenses declared: {sorted(ids)}", field="license"))

    return findings
